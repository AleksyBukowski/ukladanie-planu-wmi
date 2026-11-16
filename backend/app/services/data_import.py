"""Import danych wejściowych z transakcyjną walidacją (FR-04, FR-05, NFR-05).

Import przyjmuje komplet pięciu plików CSV/XLSX (format: `docs/import-danych-wejsciowych.md`):

    rooms        code, capacity, room_type
    groups       code, name, size
    teachers     external_id, [title], first_name, last_name
    courses      code, name
    assignments  course_code, teacher_external_id, group_code, class_type,
                 required_room_type, units_per_week

Walidacja przebiega w trzech krokach, a błędy są zbierane razem, z plikiem, wierszem i kolumną:
1. plik: format, nagłówek, wymagane kolumny (parser `tabular`),
2. wiersz: brakujące wartości, typy danych, dozwolone wartości, długość tekstu, unikalność kluczy,
3. między plikami: istnienie przedmiotu, prowadzącego i grupy z przypisania (spójność referencji)
   oraz to, czy grupa zmieści się w którejś sali wymaganego typu (pojemność, FR-07).

Zapis jest jedną transakcją (NFR-05): dotychczasowe dane wejściowe są usuwane i zastępowane
nowymi; przy jakimkolwiek błędzie – walidacji albo bazy – nic się nie zmienia. Siatka godzin
(`time_slots`) nie jest dotykana.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Assignment, ClassType, Course, Room, RoomType, StudentGroup, Teacher
from app.schemas.imports import DataImportSummary, ImportIssue
from app.services.import_errors import ImportValidationError
from app.services.tabular import TabularFileError, parse_table

# Przy całkowicie złym pliku raport mógłby mieć dziesiątki tysięcy pozycji – ucinamy go.
MAX_ISSUES = 1000

_INTEGER = re.compile(r"^[+-]?\d+$")


# --- Konwersja wartości komórek ----------------------------------------------------------------


def _text(max_length: int) -> Callable[[Any], str]:
    def parse(value: Any) -> str:
        if isinstance(value, float) and value.is_integer():
            value = int(value)  # kod „123” zapisany w XLSX jako liczba
        text = str(value).strip()
        if len(text) > max_length:
            raise ValueError(f"Tekst jest za długi ({len(text)} znaków, maksymalnie {max_length}).")
        return text

    return parse


def _integer(minimum: int, maximum: int) -> Callable[[Any], int]:
    def parse(value: Any) -> int:
        number: int | None = None
        if isinstance(value, bool):
            number = None
        elif isinstance(value, int):
            number = value
        elif isinstance(value, float) and value.is_integer():
            number = int(value)
        elif isinstance(value, str) and _INTEGER.match(value.strip()):
            number = int(value.strip())
        if number is None:
            raise ValueError(f"„{value}” nie jest liczbą całkowitą.")
        if not minimum <= number <= maximum:
            raise ValueError(f"Wartość {number} jest spoza zakresu {minimum}–{maximum}.")
        return number

    return parse


def _choice(enum_cls: type[StrEnum]) -> Callable[[Any], StrEnum]:
    allowed = ", ".join(member.value for member in enum_cls)

    def parse(value: Any) -> StrEnum:
        try:
            return enum_cls(str(value).strip().lower())
        except ValueError:
            raise ValueError(f"Nieznana wartość „{value}” – dozwolone: {allowed}.") from None

    return parse


# --- Opis plików -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Column:
    name: str
    parse: Callable[[Any], Any]
    required: bool = True  # False: kolumna może nie istnieć, a pusta komórka dostaje `default`
    default: Any = None
    references: str | None = None  # klucz pliku, w którym musi istnieć ta wartość


@dataclass(frozen=True)
class FileSpec:
    key: str
    label: str  # dopełniacz do komunikatów: „Brak pliku sal”
    columns: tuple[Column, ...]
    unique: str  # kolumna z kluczem, po którym odwołują się inne pliki

    @property
    def required_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.required]

    @property
    def optional_columns(self) -> list[str]:
        return [c.name for c in self.columns if not c.required]


SPECS: tuple[FileSpec, ...] = (
    FileSpec(
        key="rooms",
        label="sal",
        unique="code",
        columns=(
            Column("code", _text(32)),
            Column("capacity", _integer(1, 10_000)),
            Column("room_type", _choice(RoomType)),
        ),
    ),
    FileSpec(
        key="groups",
        label="grup",
        unique="code",
        columns=(
            Column("code", _text(32)),
            Column("name", _text(200)),
            Column("size", _integer(1, 10_000)),
        ),
    ),
    FileSpec(
        key="teachers",
        label="prowadzących",
        unique="external_id",
        columns=(
            Column("external_id", _text(64)),
            Column("title", _text(64), required=False, default=""),
            Column("first_name", _text(100)),
            Column("last_name", _text(100)),
        ),
    ),
    FileSpec(
        key="courses",
        label="przedmiotów",
        unique="code",
        columns=(
            Column("code", _text(64)),
            Column("name", _text(200)),
        ),
    ),
    FileSpec(
        key="assignments",
        label="przypisań",
        unique="",  # przypisania nie mają klucza – nikt się do nich nie odwołuje
        columns=(
            Column("course_code", _text(64), references="courses"),
            Column("teacher_external_id", _text(64), references="teachers"),
            Column("group_code", _text(32), references="groups"),
            Column("class_type", _choice(ClassType)),
            Column("required_room_type", _choice(RoomType)),
            Column("units_per_week", _integer(1, 50)),
        ),
    ),
)
FILE_KEYS = tuple(spec.key for spec in SPECS)
_SPECS_BY_KEY = {spec.key: spec for spec in SPECS}


# --- Walidacja ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class UploadedFile:
    content: bytes
    filename: str | None


@dataclass
class Record:
    row: int
    values: dict[str, Any]  # tylko poprawnie odczytane kolumny
    valid: bool  # wszystkie kolumny poprawne


@dataclass
class ParsedFile:
    readable: bool = False  # plik dał się wczytać i ma wymagane kolumny
    has_errors: bool = False
    records: list[Record] = field(default_factory=list)
    keys: dict[Any, Record] = field(default_factory=dict)  # unikalny klucz -> pierwszy wiersz

    @property
    def valid_records(self) -> list[Record]:
        return [record for record in self.records if record.valid]


@dataclass
class ValidatedData:
    files: dict[str, ParsedFile]

    def records(self, key: str) -> list[Record]:
        return self.files[key].valid_records


def validate_input_data(files: Mapping[str, UploadedFile | None]) -> ValidatedData:
    """Sprawdza komplet plików; zgłasza `ImportValidationError` z listą wszystkich błędów."""
    issues: list[ImportIssue] = []
    parsed = {spec.key: _parse_file(spec, files.get(spec.key), issues) for spec in SPECS}
    _check_references(parsed, issues)
    _check_capacity(parsed, issues)

    if issues:
        order = {key: index for index, key in enumerate(FILE_KEYS)}
        issues.sort(key=lambda issue: (order.get(issue.file or "", -1), issue.row or 0))
        raise ImportValidationError(
            "Import odrzucony – popraw błędy i wgraj pliki ponownie.", _truncate(issues)
        )
    return ValidatedData(files=parsed)


def _parse_file(
    spec: FileSpec, upload: UploadedFile | None, issues: list[ImportIssue]
) -> ParsedFile:
    result = ParsedFile()
    if upload is None:
        issues.append(ImportIssue(file=spec.key, message=f"Brak pliku {spec.label}."))
        result.has_errors = True
        return result

    try:
        table = parse_table(
            upload.content, upload.filename, spec.required_columns, spec.optional_columns
        )
    except TabularFileError as exc:
        issues.append(ImportIssue(file=spec.key, message=str(exc)))
        result.has_errors = True
        return result

    result.readable = True
    if not table.rows:
        issues.append(ImportIssue(file=spec.key, message=f"Plik {spec.label} nie zawiera danych."))
        result.has_errors = True

    for row in table.rows:
        values: dict[str, Any] = {}
        valid = True
        for column in spec.columns:
            raw = row.values.get(column.name)
            if raw is None:
                if column.required:
                    issues.append(_issue(spec, row.row_number, column.name, "Brak wartości."))
                    valid = False
                else:
                    values[column.name] = column.default
                continue
            try:
                values[column.name] = column.parse(raw)
            except ValueError as exc:
                issues.append(_issue(spec, row.row_number, column.name, str(exc)))
                valid = False

        record = Record(row=row.row_number, values=values, valid=valid)
        if spec.unique and spec.unique in values:
            key = values[spec.unique]
            first = result.keys.get(key)
            if first is not None:
                issues.append(
                    _issue(
                        spec,
                        row.row_number,
                        spec.unique,
                        f"Wartość „{key}” powtarza się – występuje już w wierszu {first.row}.",
                    )
                )
                record.valid = False
            else:
                result.keys[key] = record
        result.has_errors |= not record.valid
        result.records.append(record)
    return result


def _check_references(parsed: dict[str, ParsedFile], issues: list[ImportIssue]) -> None:
    for spec in SPECS:
        for column in (c for c in spec.columns if c.references):
            target = parsed[column.references]
            if not target.readable:
                continue  # brak pliku docelowego jest już zgłoszony – nie mnożymy błędów
            label = _SPECS_BY_KEY[column.references].label
            for record in parsed[spec.key].records:
                value = record.values.get(column.name)
                if value is not None and value not in target.keys:
                    issues.append(
                        _issue(
                            spec,
                            record.row,
                            column.name,
                            f"„{value}” nie występuje w pliku {label}.",
                        )
                    )
                    record.valid = False


def _check_capacity(parsed: dict[str, ParsedFile], issues: list[ImportIssue]) -> None:
    rooms, groups = parsed["rooms"], parsed["groups"]
    if rooms.has_errors or groups.has_errors:
        # Przy błędnych salach lub grupach wynik byłby mylący (np. pominięta sala z błędem).
        return

    largest: dict[RoomType, int] = {}
    for room in rooms.records:
        room_type, capacity = room.values["room_type"], room.values["capacity"]
        largest[room_type] = max(largest.get(room_type, 0), capacity)

    spec = _SPECS_BY_KEY["assignments"]
    for record in parsed["assignments"].records:
        if not record.valid:
            continue
        group = groups.keys[record.values["group_code"]].values
        room_type = record.values["required_room_type"]
        capacity = largest.get(room_type)
        if capacity is None:
            issues.append(
                _issue(
                    spec,
                    record.row,
                    "required_room_type",
                    f"W pliku sal nie ma żadnej sali typu „{room_type}”.",
                )
            )
        elif group["size"] > capacity:
            issues.append(
                _issue(
                    spec,
                    record.row,
                    "group_code",
                    f"Grupa {group['code']} liczy {group['size']} os., a największa sala typu "
                    f"„{room_type}” ma {_seats(capacity)}.",
                )
            )


def _seats(count: int) -> str:
    """Odmiana: 1 miejsce, 2–4 miejsca (bez 12–14), pozostałe – miejsc."""
    if count == 1:
        return "1 miejsce"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} miejsca"
    return f"{count} miejsc"


def _issue(spec: FileSpec, row: int, column: str, message: str) -> ImportIssue:
    return ImportIssue(file=spec.key, row=row, column=column, message=message)


def _truncate(issues: list[ImportIssue]) -> list[ImportIssue]:
    if len(issues) <= MAX_ISSUES:
        return issues
    hidden = len(issues) - MAX_ISSUES
    return [
        *issues[:MAX_ISSUES],
        ImportIssue(
            message=f"…oraz {hidden} kolejnych błędów – popraw powyższe i spróbuj ponownie."
        ),
    ]


# --- Zapis -------------------------------------------------------------------------------------


def import_input_data(db: Session, files: Mapping[str, UploadedFile | None]) -> DataImportSummary:
    """Waliduje pliki i w jednej transakcji zastępuje nimi dane wejściowe – w całości albo wcale."""
    data = validate_input_data(files)
    try:
        # Kolejność usuwania: najpierw przypisania, które odwołują się do pozostałych tabel.
        for model in (Assignment, Course, Teacher, StudentGroup, Room):
            db.execute(delete(model))

        rooms = [Room(**record.values) for record in data.records("rooms")]
        groups = {r.values["code"]: StudentGroup(**r.values) for r in data.records("groups")}
        teachers = {r.values["external_id"]: Teacher(**r.values) for r in data.records("teachers")}
        courses = {r.values["code"]: Course(**r.values) for r in data.records("courses")}
        assignments = [
            Assignment(
                course=courses[values["course_code"]],
                teacher=teachers[values["teacher_external_id"]],
                group=groups[values["group_code"]],
                class_type=values["class_type"],
                required_room_type=values["required_room_type"],
                units_per_week=values["units_per_week"],
            )
            for values in (record.values for record in data.records("assignments"))
        ]
        db.add_all([*rooms, *groups.values(), *teachers.values(), *courses.values(), *assignments])
        db.commit()
    except Exception:
        db.rollback()
        raise

    return DataImportSummary(
        rooms=len(rooms),
        groups=len(groups),
        teachers=len(teachers),
        courses=len(courses),
        assignments=len(assignments),
    )
