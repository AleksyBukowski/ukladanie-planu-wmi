"""Wspólny parser plików tabelarycznych CSV/XLSX dla importów (FR-04, FR-05).

Parser zamienia plik na listę wierszy `{kolumna: wartość}` z numerami wierszy takimi,
jakie planista widzi w arkuszu (nagłówek to zwykle wiersz 1). Nie zna znaczenia kolumn –
konwersję typów i walidację biznesową robią importery konkretnych encji (np. `time_grid`).

Zasady:
- format rozpoznawany po rozszerzeniu: `.csv` albo `.xlsx` (stary `.xls` nie jest obsługiwany),
- CSV: kodowanie UTF-8 (także z BOM) lub Windows-1250, separator `,`, `;` albo tabulator
  (rozpoznawany po wierszu nagłówka – polski Excel zapisuje CSV ze średnikiem),
- XLSX: czytany jest pierwszy arkusz, wartości formuł jako ostatnio obliczone wyniki,
- nagłówki porównywane bez wielkości liter i białych znaków na brzegach,
- puste wiersze są pomijane, puste komórki mają wartość `None`, tekst jest przycinany,
- kolumny spoza listy oczekiwanych są ignorowane.
"""

import csv
import io
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

# Zabezpieczenie przed przypadkowym wgraniem ogromnego arkusza.
MAX_DATA_ROWS = 50_000

_CSV_DELIMITERS = (",", ";", "\t")
_CSV_ENCODINGS = ("utf-8-sig", "cp1250")


class TabularFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"


class TabularFileError(ValueError):
    """Pliku nie da się wczytać jako tabeli (zły format, brak nagłówka, brak kolumn…)."""


@dataclass(frozen=True)
class ParsedRow:
    row_number: int  # numer wiersza w pliku, liczony od 1 (jak w Excelu)
    values: dict[str, Any]


@dataclass(frozen=True)
class ParsedTable:
    columns: list[str]  # oczekiwane kolumny obecne w pliku
    rows: list[ParsedRow]


def detect_format(filename: str | None) -> TabularFormat:
    suffix = PurePath(filename or "").suffix.lower()
    if suffix == ".csv":
        return TabularFormat.CSV
    if suffix == ".xlsx":
        return TabularFormat.XLSX
    if suffix == ".xls":
        raise TabularFileError(
            "Format .xls (Excel 97–2003) nie jest obsługiwany – zapisz plik jako .xlsx lub .csv."
        )
    raise TabularFileError("Nieobsługiwany format pliku – dozwolone są pliki .csv i .xlsx.")


def parse_table(
    content: bytes,
    filename: str | None,
    required_columns: Sequence[str],
    optional_columns: Sequence[str] = (),
) -> ParsedTable:
    """Wczytuje plik CSV/XLSX i zwraca wiersze danych z wymaganymi kolumnami.

    Zgłasza `TabularFileError`, gdy pliku nie da się odczytać albo brakuje kolumn.
    """
    file_format = detect_format(filename)
    if not content:
        raise TabularFileError("Plik jest pusty.")

    raw_rows = _read_csv(content) if file_format is TabularFormat.CSV else _read_xlsx(content)
    return _build_table(raw_rows, required_columns, optional_columns)


def _build_table(
    raw_rows: Iterable[tuple[int, Sequence[Any]]],
    required_columns: Sequence[str],
    optional_columns: Sequence[str],
) -> ParsedTable:
    rows_iter = (
        (number, [_clean(cell) for cell in cells])
        for number, cells in raw_rows
        if any(_clean(cell) is not None for cell in cells)
    )

    header_entry = next(rows_iter, None)
    if header_entry is None:
        raise TabularFileError("Plik nie zawiera nagłówka ani danych.")
    header_row_number, header_cells = header_entry

    header = [_normalize_header(cell) for cell in header_cells]
    duplicates = sorted({name for name in header if name and header.count(name) > 1})
    if duplicates:
        raise TabularFileError(
            f"Wiersz {header_row_number}: powtórzone kolumny w nagłówku: {', '.join(duplicates)}."
        )

    missing = [name for name in required_columns if name not in header]
    if missing:
        raise TabularFileError(
            f"Wiersz {header_row_number}: brak wymaganych kolumn: {', '.join(missing)}. "
            f"Oczekiwany nagłówek: {', '.join([*required_columns, *optional_columns])}."
        )

    expected = [*required_columns, *(c for c in optional_columns if c not in required_columns)]
    positions = {name: header.index(name) for name in expected if name in header}

    rows: list[ParsedRow] = []
    for number, cells in rows_iter:
        if len(rows) >= MAX_DATA_ROWS:
            raise TabularFileError(f"Plik ma więcej niż {MAX_DATA_ROWS} wierszy danych.")
        values = {
            name: cells[index] if index < len(cells) else None for name, index in positions.items()
        }
        rows.append(ParsedRow(row_number=number, values=values))

    return ParsedTable(columns=list(positions), rows=rows)


def _read_csv(content: bytes) -> Iterator[tuple[int, list[str]]]:
    text = _decode(content)
    # Separator wykrywamy z pierwszej niepustej linii (zwykle nagłówka).
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = max(_CSV_DELIMITERS, key=first_line.count) if first_line else ","
    if first_line.count(delimiter) == 0:
        delimiter = ","  # jedna kolumna – separator nie ma znaczenia

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        # Materializujemy, żeby błąd składni CSV pojawił się tu, a nie w dalszym przetwarzaniu.
        rows = list(enumerate(reader, start=1))
    except csv.Error as exc:
        raise TabularFileError(f"Niepoprawny plik CSV: {exc}.") from exc
    return iter(rows)


def _decode(content: bytes) -> str:
    for encoding in _CSV_ENCODINGS:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise TabularFileError("Nie udało się odczytać kodowania pliku CSV – zapisz go jako UTF-8.")


def _read_xlsx(content: bytes) -> Iterator[tuple[int, tuple[Any, ...]]]:
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise TabularFileError(
            "Nie udało się odczytać pliku XLSX – sprawdź, czy to poprawny skoroszyt Excela."
        ) from exc

    try:
        if not workbook.worksheets:
            raise TabularFileError("Skoroszyt nie zawiera żadnego arkusza.")
        sheet = workbook.worksheets[0]
        # Zapisany w pliku zakres arkusza bywa błędny (np. po eksporcie z innych programów) –
        # resetujemy go, żeby przeczytać wszystkie wiersze.
        sheet.reset_dimensions()
        # min_row=1 wymusza zwracanie pustych wierszy, więc numeracja zgadza się z Excelem.
        rows = list(enumerate(sheet.iter_rows(min_row=1, values_only=True), start=1))
    finally:
        workbook.close()
    return iter(rows)


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _normalize_header(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()
