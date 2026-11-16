"""Siatka godzin semestru (FR-03): operacje na blokach, walidacja i import z CSV/XLSX.

Reguły siatki:
- blok ma dzień tygodnia 0–6 (0 = poniedziałek) i godzinę zakończenia późniejszą niż początek,
- bloki tego samego dnia nie mogą na siebie nachodzić (stykanie się, np. 09:30 i 09:30, jest OK).

Import pliku i zastąpienie całej siatki są transakcyjne (FR-05, NFR-05): przy jakimkolwiek
błędzie nic nie jest zapisywane, a planista dostaje pełną listę błędów z numerami wierszy.

Format pliku importu (pierwszy wiersz to nagłówek, kolejność kolumn dowolna):

    day_of_week,start_time,end_time
    poniedziałek,08:00,09:30
    0,09:45,11:15

`day_of_week` – liczba 0–6 albo nazwa dnia (np. „poniedziałek”, „pon”, „pn”);
`start_time`/`end_time` – `GG:MM` (także `G.MM` lub z sekundami) albo komórka czasu w XLSX.
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TimeSlot
from app.schemas.imports import ImportIssue
from app.schemas.time_slots import DAY_NAMES, TimeSlotCreate
from app.services.import_errors import ImportValidationError
from app.services.tabular import TabularFileError, parse_table

COLUMNS = ("day_of_week", "start_time", "end_time")

_DAY_ALIASES: dict[str, int] = {
    alias: day
    for day, aliases in enumerate(
        (
            ("poniedzialek", "pon", "pn", "monday", "mon"),
            ("wtorek", "wt", "tuesday", "tue"),
            ("sroda", "sr", "wednesday", "wed"),
            ("czwartek", "czw", "cz", "thursday", "thu"),
            ("piatek", "pt", "pia", "friday", "fri"),
            ("sobota", "sob", "so", "saturday", "sat"),
            ("niedziela", "niedz", "nd", "nie", "sunday", "sun"),
        )
    )
    for alias in aliases
}
_TIME_PATTERN = re.compile(r"^(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?$")
_SECONDS_PER_DAY = 24 * 60 * 60


class TimeSlotNotFoundError(LookupError):
    pass


class TimeSlotConflictError(ValueError):
    """Blok nachodzi na inny blok tego samego dnia."""


class TimeGridValidationError(ImportValidationError):
    """Dane siatki są niepoprawne – `issues` zawiera wszystkie znalezione błędy."""


# --- Odczyt i pojedyncze bloki (FR-03, FR-06) --------------------------------------------------


def list_time_slots(db: Session) -> list[TimeSlot]:
    return list(db.scalars(select(TimeSlot).order_by(TimeSlot.day_of_week, TimeSlot.start_time)))


def get_time_slot(db: Session, slot_id: int) -> TimeSlot:
    slot = db.get(TimeSlot, slot_id)
    if slot is None:
        raise TimeSlotNotFoundError(f"Blok godzinowy o id {slot_id} nie istnieje.")
    return slot


def create_time_slot(db: Session, data: TimeSlotCreate) -> TimeSlot:
    _ensure_no_overlap(db, data)
    slot = TimeSlot(**data.model_dump())
    db.add(slot)
    _commit_slot(db, data)
    return slot


def update_time_slot(db: Session, slot_id: int, data: TimeSlotCreate) -> TimeSlot:
    slot = get_time_slot(db, slot_id)
    _ensure_no_overlap(db, data, exclude_id=slot_id)
    for field, value in data.model_dump().items():
        setattr(slot, field, value)
    _commit_slot(db, data)
    return slot


def delete_time_slot(db: Session, slot_id: int) -> None:
    db.delete(get_time_slot(db, slot_id))
    db.commit()


def _commit_slot(db: Session, data: TimeSlotCreate) -> None:
    # Sprawdzenie nakładania nie chroni przed dwoma równoczesnymi zapisami tego samego terminu –
    # wtedy zadziała ograniczenie UNIQUE(day_of_week, start_time) w bazie.
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TimeSlotConflictError(
            f"Blok {_describe(data.day_of_week, data.start_time, data.end_time)} już istnieje."
        ) from exc


def _ensure_no_overlap(db: Session, data: TimeSlotCreate, exclude_id: int | None = None) -> None:
    query = select(TimeSlot).where(
        TimeSlot.day_of_week == data.day_of_week,
        TimeSlot.start_time < data.end_time,
        TimeSlot.end_time > data.start_time,
    )
    if exclude_id is not None:
        query = query.where(TimeSlot.id != exclude_id)
    other = db.scalars(query.limit(1)).first()
    if other is not None:
        raise TimeSlotConflictError(
            f"Blok {_describe(data.day_of_week, data.start_time, data.end_time)} nachodzi na "
            f"istniejący blok {_describe(other.day_of_week, other.start_time, other.end_time)} "
            f"(id {other.id})."
        )


# --- Zastąpienie całej siatki i import z pliku -------------------------------------------------


def replace_time_grid(db: Session, slots: Sequence[TimeSlotCreate]) -> list[TimeSlot]:
    """Zastępuje całą siatkę podaną listą bloków (pozycje w raporcie błędów liczone od 1)."""
    return _replace(db, list(enumerate(slots, start=1)))


def import_time_grid(db: Session, content: bytes, filename: str | None) -> list[TimeSlot]:
    """Importuje siatkę z pliku CSV/XLSX, zastępując dotychczasową – w całości albo wcale."""
    return _replace(db, parse_time_grid_file(content, filename))


def parse_time_grid_file(content: bytes, filename: str | None) -> list[tuple[int, TimeSlotCreate]]:
    """Zamienia plik na bloki z numerami wierszy; zgłasza wszystkie błędy naraz."""
    try:
        table = parse_table(content, filename, required_columns=COLUMNS)
    except TabularFileError as exc:
        raise TimeGridValidationError(str(exc), [ImportIssue(message=str(exc))]) from exc

    entries: list[tuple[int, TimeSlotCreate]] = []
    issues: list[ImportIssue] = []
    for row in table.rows:
        row_issues: list[ImportIssue] = []
        parsed: dict[str, Any] = {}
        for column, parse in (
            ("day_of_week", _parse_day),
            ("start_time", _parse_time),
            ("end_time", _parse_time),
        ):
            value = row.values[column]
            if value is None:
                row_issues.append(
                    ImportIssue(row=row.row_number, column=column, message="Brak wartości.")
                )
                continue
            try:
                parsed[column] = parse(value)
            except ValueError as exc:
                row_issues.append(ImportIssue(row=row.row_number, column=column, message=str(exc)))

        if not row_issues:
            try:
                entries.append((row.row_number, TimeSlotCreate(**parsed)))
            except ValidationError as exc:
                row_issues.append(
                    ImportIssue(
                        row=row.row_number,
                        column="end_time",
                        message=exc.errors()[0]["msg"].removeprefix("Value error, "),
                    )
                )
        issues.extend(row_issues)

    if not table.rows:
        issues.append(ImportIssue(message="Plik nie zawiera żadnego bloku godzinowego."))
    if issues:
        raise TimeGridValidationError("Plik siatki godzin zawiera błędy.", issues)
    return entries


def _replace(db: Session, entries: list[tuple[int, TimeSlotCreate]]) -> list[TimeSlot]:
    issues = _find_overlaps(entries)
    if issues:
        raise TimeGridValidationError("Bloki siatki godzin nachodzą na siebie.", issues)

    try:
        db.execute(delete(TimeSlot))
        db.add_all(TimeSlot(**data.model_dump()) for _, data in entries)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return list_time_slots(db)


def _find_overlaps(entries: list[tuple[int, TimeSlotCreate]]) -> list[ImportIssue]:
    issues: list[ImportIssue] = []
    ordered = sorted(entries, key=lambda e: (e[1].day_of_week, e[1].start_time, e[0]))
    for i, (row, slot) in enumerate(ordered):
        for other_row, other in ordered[:i]:
            if other.day_of_week == slot.day_of_week and other.end_time > slot.start_time:
                issues.append(
                    ImportIssue(
                        row=row,
                        column="start_time",
                        message=(
                            f"Blok {_describe(slot.day_of_week, slot.start_time, slot.end_time)}"
                            f" nachodzi na blok z wiersza {other_row} "
                            f"({_fmt(other.start_time)}–{_fmt(other.end_time)})."
                        ),
                    )
                )
    issues.sort(key=lambda issue: issue.row or 0)
    return issues


# --- Konwersja wartości komórek ----------------------------------------------------------------


def _parse_day(value: Any) -> int:
    number: float | None = None
    if isinstance(value, int | float) and not isinstance(value, bool):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip().lower().rstrip(".")
        if text.isdigit():
            number = float(text)
        else:
            day = _DAY_ALIASES.get(_strip_accents(text))
            if day is not None:
                return day

    if number is not None and number.is_integer() and 0 <= number <= 6:
        return int(number)
    raise ValueError(
        f"Nieprawidłowy dzień tygodnia „{value}” – podaj liczbę 0–6 (0 = poniedziałek) "
        "lub nazwę dnia, np. „poniedziałek”, „pon”."
    )


def _parse_time(value: Any) -> time:
    # Kolejność ma znaczenie: datetime jest podklasą date, a nie time, więc sprawdzamy osobno.
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, time):
        return value.replace(tzinfo=None, microsecond=0)
    if isinstance(value, timedelta):
        return _time_from_seconds(value.total_seconds(), value)
    if isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value < 1:
        # Excel przechowuje godzinę jako ułamek doby, np. 0,375 = 09:00.
        return _time_from_seconds(value * _SECONDS_PER_DAY, value)
    if isinstance(value, str):
        match = _TIME_PATTERN.match(value.strip())
        if match:
            hours, minutes, seconds = (int(part) if part else 0 for part in match.groups())
            if hours < 24 and minutes < 60 and seconds < 60:
                return time(hours, minutes, seconds)
    raise ValueError(f"Nieprawidłowa godzina „{value}” – użyj formatu GG:MM, np. 08:00.")


def _time_from_seconds(total: float, original: Any) -> time:
    seconds = round(total)
    if not 0 <= seconds < _SECONDS_PER_DAY:
        raise ValueError(f"Nieprawidłowa godzina „{original}” – użyj formatu GG:MM, np. 08:00.")
    return time(seconds // 3600, seconds % 3600 // 60, seconds % 60)


def _strip_accents(text: str) -> str:
    text = text.replace("ł", "l")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _fmt(value: time) -> str:
    return value.strftime("%H:%M")


def _describe(day: int, start: time, end: time) -> str:
    return f"{DAY_NAMES[day]} {_fmt(start)}–{_fmt(end)}"
