from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as mock_usos


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    (tmp_path / "rooms.csv").write_text("code,capacity\nA1.12,32\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    monkeypatch.setattr(mock_usos, "DATA_DIR", tmp_path)
    return TestClient(mock_usos.app)


def test_lists_only_export_files(client: TestClient) -> None:
    assert client.get("/exports").json() == {"files": ["rooms.csv"]}


def test_serves_csv_as_json(client: TestClient) -> None:
    assert client.get("/services/rooms").json() == [{"code": "A1.12", "capacity": "32"}]


def test_downloads_export_file(client: TestClient) -> None:
    response = client.get("/exports/rooms.csv")
    assert response.status_code == 200
    assert response.text.startswith("code,capacity")


def test_unknown_file_returns_404(client: TestClient) -> None:
    assert client.get("/exports/notes.txt").status_code == 404
    assert client.get("/services/missing").status_code == 404
