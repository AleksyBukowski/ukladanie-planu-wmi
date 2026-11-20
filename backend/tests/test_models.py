from datetime import time

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    AssignmentGroup,
    ClassType,
    Course,
    Room,
    RoomType,
    StudentGroup,
    Teacher,
    TimeSlot,
    WeekType,
)


def test_assignment_links_course_teacher_and_group(db: Session) -> None:
    assignment = Assignment(
        course=Course(code="ASD", name="Algorytmy i struktury danych"),
        teacher=Teacher(title="dr", first_name="Anna", last_name="Nowak"),
        groups=[StudentGroup(code="INF-2A", name="Informatyka, rok 2, grupa A", size=28)],
        class_type=ClassType.LAB,
        required_room_type=RoomType.LAB,
        units_per_week=1,
    )
    db.add_all([assignment, Room(code="L2.03", capacity=30, room_type=RoomType.LAB)])
    db.commit()

    stored = db.scalars(select(Assignment)).one()
    assert stored.groups[0].code == "INF-2A"
    assert stored.class_type is ClassType.LAB
    assert db.scalars(select(Room)).one().room_type is RoomType.LAB


def test_time_slot_stores_times_and_default_week_type(db: Session) -> None:
    db.add(TimeSlot(day_of_week=0, start_time=time(8, 0), end_time=time(9, 30)))
    db.commit()

    slot = db.scalars(select(TimeSlot)).one()
    assert (slot.start_time, slot.end_time) == (time(8, 0), time(9, 30))
    assert slot.week_type is WeekType.ALL


def test_time_slot_allows_same_hours_for_different_week_types(
    db: Session,
) -> None:
    db.add_all(
        [
            TimeSlot(
                day_of_week=1,
                start_time=time(10, 0),
                end_time=time(11, 30),
                week_type=WeekType.ODD,
            ),
            TimeSlot(
                day_of_week=1,
                start_time=time(10, 0),
                end_time=time(11, 30),
                week_type=WeekType.EVEN,
            ),
        ]
    )
    db.commit()

    slots = db.scalars(select(TimeSlot)).all()
    assert len(slots) == 2


def test_time_slot_rejects_duplicate_day_time_and_week_type(
    db: Session,
) -> None:
    db.add(
        TimeSlot(
            day_of_week=2,
            start_time=time(8, 0),
            end_time=time(9, 30),
            week_type=WeekType.ALL,
        )
    )
    db.commit()

    db.add(
        TimeSlot(
            day_of_week=2,
            start_time=time(8, 0),
            end_time=time(9, 30),
            week_type=WeekType.ALL,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("invalid_day", [-1, 7])
def test_time_slot_rejects_invalid_day_of_week(db: Session, invalid_day: int) -> None:
    db.add(
        TimeSlot(
            day_of_week=invalid_day,
            start_time=time(8, 0),
            end_time=time(9, 30),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (time(10, 0), time(9, 30)),
        (time(10, 0), time(10, 0)),
    ],
)
def test_time_slot_rejects_invalid_time_order(db: Session, start: time, end: time) -> None:
    db.add(TimeSlot(day_of_week=0, start_time=start, end_time=end))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    ("first", "duplicate"),
    [
        (
            Room(code="A1.12", capacity=20, room_type=RoomType.CLASSROOM),
            Room(code="A1.12", capacity=40, room_type=RoomType.LECTURE_HALL),
        ),
        (
            Course(code="INF-BD2", name="Bazy danych 2"),
            Course(code="INF-BD2", name="Inny przedmiot"),
        ),
    ],
)
def test_duplicate_codes_raise_integrity_error(
    db: Session, first: object, duplicate: object
) -> None:
    db.add(first)
    db.commit()

    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    "make_invalid",
    [
        lambda: Room(code="L0.01", capacity=0, room_type=RoomType.LAB),
        lambda: StudentGroup(code="INF-0Z", name="Grupa zerowa", size=0),
        lambda: Assignment(
            course=Course(code="X1", name="Przedmiot X"),
            teacher=Teacher(first_name="A", last_name="B"),
            class_type=ClassType.LECTURE,
            required_room_type=RoomType.LECTURE_HALL,
            units_per_week=0,
        ),
    ],
    ids=["room_capacity", "student_group_size", "assignment_units_per_week"],
)
def test_check_constraint_rejects_non_positive_values(db: Session, make_invalid) -> None:
    db.add(make_invalid())
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("room_type", list(RoomType))
def test_room_type_round_trips_all_enum_values(db: Session, room_type: RoomType) -> None:
    db.add(Room(code="R1", capacity=10, room_type=room_type))
    db.commit()

    assert db.scalars(select(Room)).one().room_type is room_type


@pytest.mark.parametrize("class_type", list(ClassType))
def test_class_type_round_trips_all_enum_values(db: Session, class_type: ClassType) -> None:
    db.add(
        Assignment(
            course=Course(code="C1", name="Kurs"),
            teacher=Teacher(first_name="A", last_name="B"),
            class_type=class_type,
            required_room_type=RoomType.CLASSROOM,
            units_per_week=1,
        )
    )
    db.commit()

    assert db.scalars(select(Assignment)).one().class_type is class_type


@pytest.mark.parametrize("week_type", list(WeekType))
def test_week_type_round_trips_all_enum_values(db: Session, week_type: WeekType) -> None:
    db.add(
        TimeSlot(day_of_week=0, start_time=time(8, 0), end_time=time(9, 30), week_type=week_type)
    )
    db.commit()

    assert db.scalars(select(TimeSlot)).one().week_type is week_type


def test_deleting_assignment_cascades_to_assignment_groups(db: Session) -> None:
    assignment = Assignment(
        course=Course(code="C2", name="Kurs 2"),
        teacher=Teacher(first_name="A", last_name="B"),
        groups=[StudentGroup(code="G1", name="Grupa 1", size=10)],
        class_type=ClassType.LAB,
        required_room_type=RoomType.LAB,
        units_per_week=1,
    )
    db.add(assignment)
    db.commit()
    assert db.scalars(select(AssignmentGroup)).one() is not None

    db.delete(assignment)
    db.commit()

    assert db.scalars(select(AssignmentGroup)).first() is None
    # Grupa jako taka nie jest usuwana wraz z przypisaniem.
    assert db.scalars(select(StudentGroup)).one().code == "G1"


def test_deleting_course_cascades_to_its_assignments(db: Session) -> None:
    course = Course(code="C3", name="Kurs 3")
    db.add(
        Assignment(
            course=course,
            teacher=Teacher(first_name="A", last_name="B"),
            class_type=ClassType.LECTURE,
            required_room_type=RoomType.LECTURE_HALL,
            units_per_week=1,
        )
    )
    db.commit()

    db.delete(course)
    db.commit()

    assert db.scalars(select(Assignment)).first() is None
