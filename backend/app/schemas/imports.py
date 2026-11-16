"""Wspólne schematy importu danych: raport błędów (FR-05) i podsumowanie importu (FR-04)."""

from pydantic import BaseModel, Field


class ImportIssue(BaseModel):
    file: str | None = Field(
        default=None,
        description="Plik, którego dotyczy błąd (np. `rooms`); brak przy imporcie jednego pliku.",
    )
    row: int | None = Field(
        default=None,
        description="Numer wiersza w pliku (nagłówek = 1) albo pozycja na liście w żądaniu JSON "
        "(od 1); brak, gdy błąd dotyczy całego pliku.",
    )
    column: str | None = Field(default=None, description="Kolumna, której dotyczy błąd.")
    message: str


class ImportErrorResponse(BaseModel):
    """Odpowiedź 422: import odrzucony w całości, nic nie zostało zapisane."""

    detail: str
    errors: list[ImportIssue]


class DataImportSummary(BaseModel):
    """Liczba rekordów zapisanych przez import danych wejściowych."""

    rooms: int
    groups: int
    teachers: int
    courses: int
    assignments: int
