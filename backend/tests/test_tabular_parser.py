import io
from datetime import time

import pytest
from openpyxl import Workbook

from app.services.tabular import TabularFileError, parse_table

COLUMNS = ("code", "capacity")


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_csv_with_comma_returns_rows_with_file_row_numbers() -> None:
    content = b"code,capacity\nA0.01,120\n\nA1.12,32\n"

    table = parse_table(content, "rooms.csv", COLUMNS)

    assert [(r.row_number, r.values) for r in table.rows] == [
        (2, {"code": "A0.01", "capacity": "120"}),
        (4, {"code": "A1.12", "capacity": "32"}),
    ]


def test_csv_from_polish_excel_semicolon_and_cp1250() -> None:
    content = "Code ; Capacity;uwagi\nSala Łódź;30;zbędna kolumna\n".encode("cp1250")

    table = parse_table(content, "SALE.CSV", COLUMNS)

    assert table.rows[0].values == {"code": "Sala Łódź", "capacity": "30"}


def test_csv_utf8_bom_and_missing_trailing_cells() -> None:
    content = "﻿code,capacity\nA1\n".encode()

    table = parse_table(content, "rooms.csv", COLUMNS)

    assert table.rows[0].values == {"code": "A1", "capacity": None}


def test_xlsx_keeps_cell_types_and_row_numbers() -> None:
    content = _xlsx([["code", "capacity", "start"], ["A1", 30, time(8, 0)], [None], ["B2", 12]])

    table = parse_table(content, "rooms.xlsx", COLUMNS, optional_columns=("start",))

    assert [(r.row_number, r.values) for r in table.rows] == [
        (2, {"code": "A1", "capacity": 30, "start": time(8, 0)}),
        (4, {"code": "B2", "capacity": 12, "start": None}),
    ]


def test_xlsx_header_does_not_have_to_start_in_first_row() -> None:
    content = _xlsx([[], ["code", "capacity"], ["A1", 30]])

    table = parse_table(content, "rooms.xlsx", COLUMNS)

    assert table.rows[0].row_number == 3


@pytest.mark.parametrize(
    ("content", "filename", "message"),
    [
        (b"code,capacity\n", "rooms.txt", "Nieobsługiwany format"),
        (b"code,capacity\n", "rooms.xls", ".xls"),
        (b"", "rooms.csv", "pusty"),
        (b"\n\n", "rooms.csv", "nagłówka"),
        (b"code\nA1\n", "rooms.csv", "brak wymaganych kolumn: capacity"),
        (b"code,capacity,Code\n", "rooms.csv", "powtórzone kolumny"),
        (b"not a zip file", "rooms.xlsx", "XLSX"),
    ],
)
def test_invalid_files_raise_readable_error(content: bytes, filename: str, message: str) -> None:
    with pytest.raises(TabularFileError, match=message):
        parse_table(content, filename, COLUMNS)


def test_csv_delimiter_is_detected_from_first_non_empty_line() -> None:
    content = b"\n\ncode;capacity\nA1;30\n"

    table = parse_table(content, "rooms.csv", COLUMNS)

    assert [(r.row_number, r.values) for r in table.rows] == [(4, {"code": "A1", "capacity": "30"})]
