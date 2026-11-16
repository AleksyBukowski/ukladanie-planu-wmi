"""Endpointy siatki godzin semestru (FR-03).

TODO(FR-01/FR-02): po dodaniu logowania operacje zapisu ograniczyć do roli administratora.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.imports import ImportErrorResponse
from app.schemas.time_slots import TimeGridImportResult, TimeSlotCreate, TimeSlotRead
from app.services import time_grid
from app.services.time_grid import (
    TimeGridValidationError,
    TimeSlotConflictError,
    TimeSlotNotFoundError,
)

# Limit rozmiaru wgrywanego pliku – siatka to kilkadziesiąt wierszy, 5 MB to duży zapas.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix="/time-slots", tags=["siatka godzin"])

_NOT_FOUND = {404: {"description": "Blok nie istnieje"}}
_CONFLICT = {409: {"description": "Blok nachodzi na inny blok tego samego dnia"}}
_GRID_ERRORS = {
    422: {"model": ImportErrorResponse, "description": "Błędy danych – nic nie zapisano"}
}


@router.get("", response_model=list[TimeSlotRead])
def list_time_slots(db: Session = Depends(get_db)) -> list[TimeSlotRead]:
    """Cała siatka godzin, posortowana po dniu i godzinie rozpoczęcia."""
    return [TimeSlotRead.model_validate(slot) for slot in time_grid.list_time_slots(db)]


@router.put("", response_model=list[TimeSlotRead], responses=_GRID_ERRORS)
def replace_time_grid(
    slots: list[TimeSlotCreate], db: Session = Depends(get_db)
) -> list[TimeSlotRead] | JSONResponse:
    """Zastępuje całą siatkę podaną listą bloków (w całości albo wcale)."""
    try:
        result = time_grid.replace_time_grid(db, slots)
    except TimeGridValidationError as exc:
        return _grid_error_response(exc)
    return [TimeSlotRead.model_validate(slot) for slot in result]


@router.post(
    "/import",
    response_model=TimeGridImportResult,
    responses={**_GRID_ERRORS, 413: {"description": "Plik jest za duży"}},
)
def import_time_grid(
    file: UploadFile, db: Session = Depends(get_db)
) -> TimeGridImportResult | JSONResponse:
    """Importuje siatkę z pliku CSV lub XLSX i zastępuje nią dotychczasową.

    Wymagane kolumny: `day_of_week` (0–6 lub nazwa dnia), `start_time`, `end_time` (GG:MM).
    Przy błędach zwraca listę błędów z numerami wierszy i niczego nie zapisuje (FR-05).
    """
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"Plik jest za duży – maksymalny rozmiar to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    try:
        result = time_grid.import_time_grid(db, content, file.filename)
    except TimeGridValidationError as exc:
        return _grid_error_response(exc)
    return TimeGridImportResult(
        imported=len(result),
        time_slots=[TimeSlotRead.model_validate(slot) for slot in result],
    )


@router.post(
    "", response_model=TimeSlotRead, status_code=status.HTTP_201_CREATED, responses=_CONFLICT
)
def create_time_slot(data: TimeSlotCreate, db: Session = Depends(get_db)) -> TimeSlotRead:
    try:
        slot = time_grid.create_time_slot(db, data)
    except TimeSlotConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return TimeSlotRead.model_validate(slot)


@router.get("/{slot_id}", response_model=TimeSlotRead, responses=_NOT_FOUND)
def get_time_slot(slot_id: int, db: Session = Depends(get_db)) -> TimeSlotRead:
    try:
        return TimeSlotRead.model_validate(time_grid.get_time_slot(db, slot_id))
    except TimeSlotNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.put("/{slot_id}", response_model=TimeSlotRead, responses={**_NOT_FOUND, **_CONFLICT})
def update_time_slot(
    slot_id: int, data: TimeSlotCreate, db: Session = Depends(get_db)
) -> TimeSlotRead:
    try:
        slot = time_grid.update_time_slot(db, slot_id, data)
    except TimeSlotNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except TimeSlotConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return TimeSlotRead.model_validate(slot)


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_NOT_FOUND)
def delete_time_slot(slot_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        time_grid.delete_time_slot(db, slot_id)
    except TimeSlotNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _grid_error_response(exc: TimeGridValidationError) -> JSONResponse:
    body = ImportErrorResponse(detail=exc.message, errors=exc.issues)
    return JSONResponse(status_code=422, content=body.model_dump())
