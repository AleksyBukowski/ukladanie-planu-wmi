"""Import danych wejściowych z plików CSV/XLSX (FR-04, FR-05).

TODO(FR-01/FR-02): po dodaniu logowania import ograniczyć do roli planisty.
"""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.uploads import IMPORT_ERROR_RESPONSES, import_error_response, read_upload
from app.db.session import get_db
from app.schemas.imports import DataImportSummary
from app.services import data_import
from app.services.import_errors import ImportValidationError

router = APIRouter(prefix="/imports", tags=["import danych"])


@router.post("", response_model=DataImportSummary, responses=IMPORT_ERROR_RESPONSES)
def import_input_data(
    rooms: UploadFile | None = File(None, description="Sale: code, capacity, room_type"),
    groups: UploadFile | None = File(None, description="Grupy: code, name, size"),
    teachers: UploadFile | None = File(
        None, description="Prowadzący: external_id, [title], first_name, last_name"
    ),
    courses: UploadFile | None = File(None, description="Przedmioty: code, name"),
    assignments: UploadFile | None = File(
        None,
        description="Przypisania: course_code, teacher_external_id, group_code, class_type, "
        "required_room_type, units_per_week",
    ),
    db: Session = Depends(get_db),
) -> DataImportSummary | JSONResponse:
    """Importuje komplet danych wejściowych i zastępuje nimi dotychczasowe – w całości albo wcale.

    Wymagane są wszystkie pięć plików (CSV lub XLSX). Przy błędach zwraca 422 z listą błędów
    (plik, wiersz, kolumna) i niczego nie zapisuje. Siatka godzin pozostaje bez zmian.
    """
    uploads = {
        "rooms": rooms,
        "groups": groups,
        "teachers": teachers,
        "courses": courses,
        "assignments": assignments,
    }
    files = {
        key: data_import.UploadedFile(content=read_upload(upload), filename=upload.filename)
        for key, upload in uploads.items()
        if upload is not None
    }
    try:
        return data_import.import_input_data(db, files)
    except ImportValidationError as exc:
        return import_error_response(exc)
