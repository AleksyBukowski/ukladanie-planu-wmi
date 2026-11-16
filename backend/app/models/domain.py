"""Wstępny model danych wejściowych (FR-03, FR-04).

To punkt startowy uzgodniony na poziomie architektury – tickety mogą go rozszerzać
(np. o pola wynikające ze specyfikacji importu D-03). Zmiany w modelu zgłaszaj w PR,
żeby reszta zespołu wiedziała, że trzeba odtworzyć bazę (patrz README → „Zmiany w modelu”).

Plan (wersje, przydziały terminów), niedostępności prowadzących i konta użytkowników
zostaną dodane w osobnych ticketach.
"""

import enum
from datetime import time

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClassType(enum.StrEnum):
    """Forma zajęć."""

    LECTURE = "lecture"  # wykład
    EXERCISES = "exercises"  # ćwiczenia
    LAB = "lab"  # laboratorium


class RoomType(enum.StrEnum):
    """Typ sali – zajęcia wymagają sali odpowiedniego typu (FR-07)."""

    LECTURE_HALL = "lecture_hall"  # sala wykładowa
    CLASSROOM = "classroom"  # sala ćwiczeniowa
    LAB = "lab"  # pracownia komputerowa / laboratorium


class WeekType(enum.StrEnum):
    """Częstotliwość odbywania się zajęć w cyklu tygodniowym."""

    ALL = "all"  # co tydzień
    ODD = "odd"  # tygodnie nieparzyste
    EVEN = "even"  # tygodnie parzyste


def _enum(enum_cls: type[enum.Enum]) -> Enum:
    # native_enum=False → zwykły VARCHAR + CHECK; łatwiej dodawać wartości i działa w SQLite.
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
    )


class TimeSlot(Base):
    """Blok godzinowy siatki semestru, np. poniedziałek 08:00–09:30 (FR-03)."""

    __tablename__ = "time_slots"
    __table_args__ = (
        UniqueConstraint(
            "day_of_week",
            "start_time",
            "end_time",
            "week_type",
            name="uq_time_slots_day_start_end_week",
        ),
        CheckConstraint(
            "day_of_week BETWEEN 0 AND 6", name="ck_time_slots_day_of_week"
        ),
        CheckConstraint(
            "start_time < end_time", name="ck_time_slots_start_before_end"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day_of_week: Mapped[int]  # 0 = poniedziałek … 6 = niedziela
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    week_type: Mapped[WeekType] = mapped_column(
        _enum(WeekType), default=WeekType.ALL
    )


class Room(Base):
    """Sala dydaktyczna wraz z pojemnością i przeznaczeniem."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # np. "A1.12"
    capacity: Mapped[int]
    room_type: Mapped[RoomType] = mapped_column(_enum(RoomType))


class StudentGroup(Base):
    """Grupa zajęciowa – przechowujemy tylko liczebność, bez danych studentów (NFR-04)."""

    __tablename__ = "student_groups"
    __table_args__ = (
        CheckConstraint("size > 0", name="ck_student_groups_size_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # np. "INF-2A"
    name: Mapped[str] = mapped_column(String(200))
    size: Mapped[int]

    assignments: Mapped[list["Assignment"]] = relationship(
        secondary="assignment_groups",
        back_populates="groups",
    )


class Teacher(Base):
    """Prowadzący zajęcia dydaktyczne."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(
        String(64), unique=True
    )  # id z USOS
    title: Mapped[str] = mapped_column(String(64), default="")  # np. "dr inż."
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="teacher"
    )


class Course(Base):
    """Przedmiot z programu studiów."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course"
    )


class AssignmentGroup(Base):
    """Tabela łącząca przypisania zajęć (Assignment) z grupami studenckimi (relacja M:N)."""

    __tablename__ = "assignment_groups"

    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("student_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Assignment(Base):
    """Przypisanie prowadzący-przedmiot-grupa: zajęcia do rozplanowania (FR-04).

    `units_per_week` – ile bloków tygodniowo trzeba przydzielić tym zajęciom.
    """

    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint(
            "units_per_week > 0", name="ck_assignments_units_per_week_positive"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE")
    )
    class_type: Mapped[ClassType] = mapped_column(_enum(ClassType))
    required_room_type: Mapped[RoomType] = mapped_column(_enum(RoomType))
    units_per_week: Mapped[int] = mapped_column(default=1)

    course: Mapped[Course] = relationship(back_populates="assignments")
    teacher: Mapped[Teacher] = relationship(back_populates="assignments")
    groups: Mapped[list[StudentGroup]] = relationship(
        secondary="assignment_groups",
        back_populates="assignments",
    )
