import io
from datetime import time

from fastapi.testclient import TestClient
from openpyxl import Workbook

URL = "/api/time-slots"


def _slot(day: int, start: str, end: str) -> dict[str, object]:
    return {"day_of_week": day, "start_time": start, "end_time": end}


def _upload(client: TestClient, content: bytes, filename: str = "siatka.csv"):
    return client.post(f"{URL}/import", files={"file": (filename, content)})


# --- CRUD ---------------------------------------------------------------------------------------


def test_create_list_update_and_delete_time_slot(client: TestClient) -> None:
    created = client.post(URL, json=_slot(1, "09:45", "11:15"))
    assert created.status_code == 201
    slot_id = created.json()["id"]
    client.post(URL, json=_slot(0, "08:00", "09:30"))

    listed = client.get(URL).json()
    assert [(s["day_of_week"], s["start_time"]) for s in listed] == [
        (0, "08:00:00"),
        (1, "09:45:00"),
    ]

    updated = client.put(f"{URL}/{slot_id}", json=_slot(1, "10:00", "11:30"))
    assert updated.status_code == 200
    assert updated.json() == {"id": slot_id, **_slot(1, "10:00:00", "11:30:00")}
    assert client.get(f"{URL}/{slot_id}").json()["start_time"] == "10:00:00"

    assert client.delete(f"{URL}/{slot_id}").status_code == 204
    assert client.get(f"{URL}/{slot_id}").status_code == 404


def test_missing_slot_returns_404(client: TestClient) -> None:
    assert client.get(f"{URL}/999").status_code == 404
    assert client.put(f"{URL}/999", json=_slot(0, "08:00", "09:30")).status_code == 404
    assert client.delete(f"{URL}/999").status_code == 404


def test_overlapping_slot_is_rejected_with_409(client: TestClient) -> None:
    client.post(URL, json=_slot(0, "08:00", "09:30"))

    response = client.post(URL, json=_slot(0, "09:00", "10:30"))

    assert response.status_code == 409
    assert "nachodzi" in response.json()["detail"]
    # Stykające się bloki i ten sam termin innego dnia są dozwolone.
    assert client.post(URL, json=_slot(0, "09:30", "11:00")).status_code == 201
    assert client.post(URL, json=_slot(1, "08:00", "09:30")).status_code == 201


def test_update_does_not_conflict_with_itself(client: TestClient) -> None:
    slot_id = client.post(URL, json=_slot(0, "08:00", "09:30")).json()["id"]

    response = client.put(f"{URL}/{slot_id}", json=_slot(0, "08:15", "09:45"))

    assert response.status_code == 200


def test_invalid_slot_data_is_rejected(client: TestClient) -> None:
    assert client.post(URL, json=_slot(0, "10:00", "09:00")).status_code == 422
    assert client.post(URL, json=_slot(7, "08:00", "09:30")).status_code == 422


# --- Zastąpienie całej siatki ------------------------------------------------------------------


def test_replace_grid_swaps_all_slots(client: TestClient) -> None:
    client.post(URL, json=_slot(4, "18:00", "19:30"))

    response = client.put(URL, json=[_slot(0, "08:00", "09:30"), _slot(0, "09:45", "11:15")])

    assert response.status_code == 200
    assert [s["start_time"] for s in client.get(URL).json()] == ["08:00:00", "09:45:00"]


def test_replace_grid_with_overlaps_changes_nothing(client: TestClient) -> None:
    client.post(URL, json=_slot(4, "18:00", "19:30"))

    response = client.put(URL, json=[_slot(0, "08:00", "09:30"), _slot(0, "08:00", "09:30")])

    assert response.status_code == 422
    assert response.json()["errors"][0]["row"] == 2
    assert len(client.get(URL).json()) == 1


# --- Import z pliku ----------------------------------------------------------------------------


def test_import_csv_replaces_grid(client: TestClient) -> None:
    client.post(URL, json=_slot(5, "08:00", "09:30"))
    content = (
        "day_of_week;start_time;end_time\n"
        "poniedziałek;8:00;9.30\n"
        "0;09:45;11:15\n"
        "Wt;08:00:00;09:30\n"
    ).encode()

    response = _upload(client, content)

    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 3
    assert [(s["day_of_week"], s["start_time"], s["end_time"]) for s in body["time_slots"]] == [
        (0, "08:00:00", "09:30:00"),
        (0, "09:45:00", "11:15:00"),
        (1, "08:00:00", "09:30:00"),
    ]
    assert len(client.get(URL).json()) == 3


def test_import_xlsx_with_time_cells(client: TestClient) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Day_of_week", "start_time", "end_time"])
    sheet.append([2, time(8, 0), time(9, 30)])
    sheet.append(["piątek", "11:30", 0.53125])  # 0,53125 doby = 12:45
    buffer = io.BytesIO()
    workbook.save(buffer)

    response = _upload(client, buffer.getvalue(), "siatka.xlsx")

    assert response.status_code == 200
    assert [(s["day_of_week"], s["end_time"]) for s in response.json()["time_slots"]] == [
        (2, "09:30:00"),
        (4, "12:45:00"),
    ]


def test_import_reports_all_errors_with_row_numbers_and_saves_nothing(
    client: TestClient,
) -> None:
    client.post(URL, json=_slot(5, "08:00", "09:30"))
    content = (
        b"day_of_week,start_time,end_time\n"
        b"pon,08:00,09:30\n"
        b"funday,25:00,\n"
        b"wt,11:00,10:00\n"
        b"pon,09:00,10:30\n"
    )

    response = _upload(client, content)

    assert response.status_code == 422
    errors = [(e["row"], e["column"]) for e in response.json()["errors"]]
    assert errors == [
        (3, "day_of_week"),
        (3, "start_time"),
        (3, "end_time"),
        (4, "end_time"),
    ]
    assert [s["day_of_week"] for s in client.get(URL).json()] == [5]


def test_import_reports_overlaps_between_rows(client: TestClient) -> None:
    content = b"day_of_week,start_time,end_time\npon,08:00,09:30\npon,09:00,10:30\n"

    response = _upload(client, content)

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["row"] == 3
    assert "wiersza 2" in error["message"]


def test_import_rejects_unreadable_file(client: TestClient) -> None:
    response = _upload(client, b"day,start\n", "siatka.csv")

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["row"] is None
    assert "brak wymaganych kolumn" in error["message"]


def test_import_rejects_empty_grid(client: TestClient) -> None:
    response = _upload(client, b"day_of_week,start_time,end_time\n")

    assert response.status_code == 422


def test_import_rejects_too_large_file(client: TestClient, monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(uploads, "MAX_UPLOAD_BYTES", 10)

    response = _upload(client, b"day_of_week,start_time,end_time\n")

    assert response.status_code == 413


def test_time_with_timezone_is_rejected(client: TestClient) -> None:
    response = client.post(URL, json=_slot(0, "08:00+02:00", "09:30+02:00"))

    assert response.status_code == 422
    assert client.get(URL).json() == []


def test_duplicate_caught_by_database_returns_409(client: TestClient, monkeypatch) -> None:
    from app.services import time_grid

    # Symulacja wyścigu: dwa równoczesne żądania przechodzą sprawdzenie nakładania,
    # więc duplikat zatrzymuje dopiero ograniczenie UNIQUE w bazie.
    monkeypatch.setattr(time_grid, "_ensure_no_overlap", lambda *args, **kwargs: None)
    assert client.post(URL, json=_slot(0, "08:00", "09:30")).status_code == 201

    response = client.post(URL, json=_slot(0, "08:00", "09:30"))

    assert response.status_code == 409
    assert "już istnieje" in response.json()["detail"]
    assert len(client.get(URL).json()) == 1
