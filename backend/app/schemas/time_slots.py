"""Schematy siatki godzin semestru (FR-03)."""

from datetime import time
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DAY_NAMES = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")


class TimeSlotCreate(BaseModel):
    """Blok godzinowy – używany przy tworzeniu i pełnej aktualizacji (PUT)."""

    day_of_week: int = Field(ge=0, le=6, description="0 = poniedziałek … 6 = niedziela")
    start_time: time = Field(examples=["08:00"])
    end_time: time = Field(examples=["09:30"])

    @field_validator("start_time", "end_time")
    @classmethod
    def _local_time(cls, value: time) -> time:
        # Siatka jest w czasie lokalnym wydziału. Strefa czasowa w kolumnie TIME zachowywałaby
        # się różnie w SQLite i PostgreSQL, więc ją odrzucamy.
        if value.tzinfo is not None:
            raise ValueError("Podaj godzinę bez strefy czasowej, np. 08:00.")
        return value

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("Godzina zakończenia musi być późniejsza niż godzina rozpoczęcia.")
        return self


class TimeSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day_of_week: int
    start_time: time
    end_time: time


class TimeGridImportResult(BaseModel):
    imported: int = Field(description="Liczba bloków w nowej siatce.")
    time_slots: list[TimeSlotRead]
