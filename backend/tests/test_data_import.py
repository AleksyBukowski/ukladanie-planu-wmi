import io
from datetime import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Assignment, ClassType, Room, RoomType, StudentGroup, Teacher, TimeSlot
from app.services import data_import
from app.services.data_import import UploadedFile

URL = "/api/imports"
SAMPLE_DATA = Path(__file__).resolve().parents[2] / "data" / "usos-export"

VALID = {
    "rooms": "code,capacity,room_type\nA0.01,120,lecture_hall\nA1.12,32,classroom\nL2.03,30,lab\n",
    "groups": 'code,name,size\nINF-2A,"Informatyka, rok 2, grupa A",28\nINF-2B,Inf 2B,26\n',
    "teachers": (
        "external_id,title,first_name,last_name\nT001,dr,Anna,Nowak\nT002,,Piotr,Zieliński\n"
    ),
    "courses": "code,name\nASD,Algorytmy i struktury danych\nBD,Bazy danych\n",
    "assignments": (
        "course_code,teacher_external_id,group_code,class_type,required_room_type,units_per_week\n"
        "ASD,T001,INF-2A,lab,lab,1\n"
        "BD,T002,INF-2B,exercises,classroom,2\n"
        "ASD,T001,INF-2A,lecture,lecture_hall,1\n"
    ),
}


def _files(**overrides: str | bytes | None) -> dict[str, tuple[str, bytes]]:
    files = {}
    for key, content in {**VALID, **overrides}.items():
        if content is None:
            continue
        data = content.encode() if isinstance(content, str) else content
        filename = f"{key}.xlsx" if data.startswith(b"PK") else f"{key}.csv"
        files[key] = (filename, data)
    return files


def _errors(response) -> list[tuple[str | None, int | None, str | None]]:
    assert response.status_code == 422, response.text
    return [(e["file"], e["row"], e["column"]) for e in response.json()["errors"]]


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model))


# --- Poprawny import ---------------------------------------------------------------------------


def test_import_saves_all_entities_with_relations(client: TestClient, db: Session) -> None:
    response = client.post(URL, files=_files())

    assert response.status_code == 200
    assert response.json() == {
        "rooms": 3,
        "groups": 2,
        "teachers": 2,
        "courses": 2,
        "assignments": 3,
    }
    lab = db.scalars(select(Assignment).where(Assignment.class_type == ClassType.LAB)).one()
    assert (lab.course.code, lab.teacher.last_name, lab.group.size) == ("ASD", "Nowak", 28)
    assert lab.required_room_type is RoomType.LAB
    assert db.scalars(select(Teacher).where(Teacher.external_id == "T002")).one().title == ""


def test_import_accepts_xlsx_and_missing_optional_title_column(client: TestClient) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["code", "capacity", "room_type"])
    sheet.append(["A0.01", 120, "Lecture_Hall"])
    sheet.append(["A1.12", 32.0, "classroom"])
    sheet.append(["L2.03", 30, "lab"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    response = client.post(
        URL,
        files=_files(
            rooms=buffer.getvalue(),
            teachers="external_id;first_name;last_name\nT001;Anna;Nowak\nT002;Piotr;Zieliński\n",
        ),
    )

    assert response.status_code == 200, response.text


def test_import_replaces_previous_data_and_keeps_time_grid(client: TestClient, db: Session) -> None:
    client.post(URL, files=_files())
    db.add(TimeSlot(day_of_week=0, start_time=time(8, 0), end_time=time(9, 30)))
    db.commit()

    response = client.post(
        URL,
        files=_files(
            assignments=(
                "course_code,teacher_external_id,group_code,class_type,required_room_type,"
                "units_per_week\nBD,T002,INF-2B,exercises,classroom,1\n"
            )
        ),
    )

    assert response.status_code == 200
    db.expire_all()
    assert _count(db, Assignment) == 1
    assert _count(db, Room) == 3
    assert _count(db, TimeSlot) == 1


def test_sample_export_from_repository_is_valid(client: TestClient) -> None:
    files = {
        key: (f"{key}.csv", (SAMPLE_DATA / f"{key}.csv").read_bytes())
        for key in data_import.FILE_KEYS
    }

    assert client.post(URL, files=files).status_code == 200


# --- Błędy plików i wierszy --------------------------------------------------------------------


def test_missing_and_unreadable_files_are_reported_together(client: TestClient) -> None:
    response = client.post(URL, files=_files(rooms=None, courses=None, groups="kod,nazwa\nX,Y\n"))

    errors = _errors(response)
    assert errors == [("rooms", None, None), ("groups", None, None), ("courses", None, None)]
    messages = [e["message"] for e in response.json()["errors"]]
    assert messages[0] == "Brak pliku sal."
    assert "brak wymaganych kolumn" in messages[1]


def test_row_errors_report_file_row_and_column(client: TestClient) -> None:
    response = client.post(
        URL,
        files=_files(
            rooms=(
                "code,capacity,room_type\n"
                "A0.01,120,lecture_hall\n"
                "A1.12,dużo,classroom\n"  # wiersz 3: zły typ
                "L2.03,0,lab\n"  # wiersz 4: poza zakresem
                ",30,gym\n"  # wiersz 5: brak kodu, nieznany typ
                "A0.01,50,classroom\n"  # wiersz 6: powtórzony kod
            ),
            courses=f"code,name\nASD,{'x' * 201}\nBD,Bazy danych\n",
        ),
    )

    assert _errors(response) == [
        ("rooms", 3, "capacity"),
        ("rooms", 4, "capacity"),
        ("rooms", 5, "code"),
        ("rooms", 5, "room_type"),
        ("rooms", 6, "code"),
        ("courses", 2, "name"),
    ]
    messages = [e["message"] for e in response.json()["errors"]]
    assert "nie jest liczbą całkowitą" in messages[0]
    assert "dozwolone: lecture_hall, classroom, lab" in messages[3]
    assert "występuje już w wierszu 2" in messages[4]


def test_empty_data_file_is_rejected(client: TestClient) -> None:
    response = client.post(URL, files=_files(courses="code,name\n"))

    assert ("courses", None, None) in _errors(response)


# --- Spójność referencji i pojemność sal -------------------------------------------------------


def test_unknown_references_in_assignments(client: TestClient) -> None:
    response = client.post(
        URL,
        files=_files(
            assignments=(
                "course_code,teacher_external_id,group_code,class_type,required_room_type,"
                "units_per_week\n"
                "ASD,T001,INF-2A,lab,lab,1\n"
                "XYZ,T999,INF-9Z,lab,lab,1\n"
            )
        ),
    )

    assert _errors(response) == [
        ("assignments", 3, "course_code"),
        ("assignments", 3, "teacher_external_id"),
        ("assignments", 3, "group_code"),
    ]
    assert response.json()["errors"][0]["message"] == "„XYZ” nie występuje w pliku przedmiotów."


def test_group_must_fit_in_some_room_of_required_type(client: TestClient) -> None:
    response = client.post(
        URL,
        files=_files(
            groups="code,name,size\nINF-2A,Inf 2A,31\nINF-2B,Inf 2B,26\n",
            rooms="code,capacity,room_type\nA0.01,120,lecture_hall\nL2.03,30,lab\n",
        ),
    )

    errors = response.json()["errors"]
    assert _errors(response) == [
        ("assignments", 2, "group_code"),
        ("assignments", 3, "required_room_type"),
    ]
    assert errors[0]["message"] == (
        "Grupa INF-2A liczy 31 os., a największa sala typu „lab” ma 30 miejsc."
    )
    assert "nie ma żadnej sali typu „classroom”" in errors[1]["message"]


def test_capacity_is_not_checked_when_rooms_file_has_errors(client: TestClient) -> None:
    response = client.post(
        URL,
        files=_files(rooms="code,capacity,room_type\nA0.01,120,lecture_hall\nL2.03,?,lab\n"),
    )

    # Tylko błąd w pliku sal – bez mylących błędów pojemności w przypisaniach.
    assert _errors(response) == [("rooms", 3, "capacity")]


# --- Transakcyjność (NFR-05) -------------------------------------------------------------------


def test_failed_validation_leaves_previous_data_untouched(client: TestClient, db: Session) -> None:
    client.post(URL, files=_files())

    response = client.post(URL, files=_files(groups="code,name,size\nINF-2A,Inf 2A,abc\n"))

    assert response.status_code == 422
    assert _count(db, StudentGroup) == 2
    assert _count(db, Assignment) == 3


def test_database_error_during_save_rolls_back_everything(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post(URL, files=_files())

    def broken_assignment(**kwargs: object) -> Assignment:
        raise RuntimeError("symulowana awaria bazy w trakcie zapisu")

    monkeypatch.setattr(data_import, "Assignment", broken_assignment)
    files = {
        key: UploadedFile(content=content.encode(), filename=f"{key}.csv")
        for key, content in VALID.items()
    }
    session = SessionLocal()
    try:
        with pytest.raises(RuntimeError):
            data_import.import_input_data(session, files)
    finally:
        session.close()

    # Usunięcie starych danych zostało wycofane razem z resztą zapisu.
    check = SessionLocal()
    try:
        assert _count(check, Room) == 3
        assert _count(check, Assignment) == 3
    finally:
        check.close()


def test_report_is_truncated_for_hopeless_files(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data_import, "MAX_ISSUES", 2)

    response = client.post(URL, files=_files(rooms=None, groups=None, teachers=None))

    errors = response.json()["errors"]
    assert len(errors) == 3
    assert "kolejnych błędów" in errors[-1]["message"]
