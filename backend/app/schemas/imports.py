"""Wspólne schematy raportu błędów importu (FR-05)."""

from pydantic import BaseModel, Field


class ImportIssue(BaseModel):
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
