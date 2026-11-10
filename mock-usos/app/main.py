"""Mock USOS – zastępuje prawdziwy system USOS w środowisku deweloperskim.

Nie mamy dostępu do USOS API (poza zakresem MVP, sekcja 2.2 wymagań), więc ten serwis
udaje źródło danych, z którego dziekanat pobiera eksport. Działa wyłącznie w trybie
odczytu i serwuje pliki z katalogu `data/usos-export/` (montowanego jako /data):

- GET /exports                 – lista plików eksportu,
- GET /exports/{name}          – pobranie pliku (CSV/XLSX) „tak jak z USOS”,
- GET /services/{resource}     – zawartość pliku CSV jako JSON (np. /services/rooms).

Zawartość katalogu generuje skrypt danych syntetycznych (D-10) zgodnie z formatem D-03.
"""

import csv
import io
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

DATA_DIR = Path(os.environ.get("MOCK_USOS_DATA_DIR", "/data"))
ALLOWED_SUFFIXES = {".csv", ".xlsx"}

app = FastAPI(title="Mock USOS (tylko odczyt)", version="0.1.0")


def _export_files() -> dict[str, Path]:
    if not DATA_DIR.is_dir():
        return {}
    return {
        path.name: path
        for path in sorted(DATA_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
    }


def _get_file(name: str) -> Path:
    # Szukamy tylko wśród istniejących plików – chroni przed path traversal.
    path = _export_files().get(name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Brak pliku eksportu: {name}")
    return path


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/exports")
def list_exports() -> dict[str, list[str]]:
    return {"files": list(_export_files())}


@app.get("/exports/{name}")
def download_export(name: str) -> FileResponse:
    return FileResponse(_get_file(name), filename=name)


@app.get("/services/{resource}")
def get_resource(resource: str) -> list[dict[str, str]]:
    path = _get_file(f"{resource}.csv")
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))
