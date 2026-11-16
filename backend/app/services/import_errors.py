"""Wspólny wyjątek importów – niesie pełną listę błędów dla raportu (FR-05)."""

from app.schemas.imports import ImportIssue


class ImportValidationError(ValueError):
    """Dane importu są niepoprawne – nic nie zapisano, `issues` zawiera wszystkie błędy."""

    def __init__(self, message: str, issues: list[ImportIssue]) -> None:
        super().__init__(message)
        self.message = message
        self.issues = issues
