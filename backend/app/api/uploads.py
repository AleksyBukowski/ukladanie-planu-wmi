"""Obsługa wgrywanych plików wspólna dla endpointów importu."""

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.imports import ImportErrorResponse
from app.services.import_errors import ImportValidationError

# Limit rozmiaru jednego pliku – zbiór referencyjny (D-10) to kilkadziesiąt kB, 5 MB to duży zapas.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

IMPORT_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    413: {"description": "Plik jest za duży"},
    422: {"model": ImportErrorResponse, "description": "Błędy danych – nic nie zapisano"},
}


def read_upload(file: UploadFile, max_bytes: int | None = None) -> bytes:
    """Wczytuje plik z żądania; zgłasza 413, gdy przekracza limit."""
    limit = MAX_UPLOAD_BYTES if max_bytes is None else max_bytes
    content = file.file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            413,
            f"Plik „{file.filename}” jest za duży – maksymalny rozmiar to "
            f"{limit / (1024 * 1024):g} MB.",
        )
    return content


def import_error_response(exc: ImportValidationError) -> JSONResponse:
    body = ImportErrorResponse(detail=exc.message, errors=exc.issues)
    return JSONResponse(status_code=422, content=body.model_dump())
