from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    ClassType,
    Course,
    Room,
    RoomType,
    StudentGroup,
    Teacher,
    TimeSlot,
)


def test_assignment_links_course_teacher_and_group(db: Session) -> None:
    assignment = Assignment(
        course=Course(code="ASD", name="Algorytmy i struktury danych"),
        teacher=Teacher(title="dr", first_name="Anna", last_name="Nowak"),
        group=StudentGroup(code="INF-2A", name="Informatyka, rok 2, grupa A", size=28),
        class_type=ClassType.LAB,
        required_room_type=RoomType.LAB,
        units_per_week=1,
    )
    db.add_all([assignment, Room(code="L2.03", capacity=30, room_type=RoomType.LAB)])
    db.commit()

    stored = db.scalars(select(Assignment)).one()
    assert stored.group.code == "INF-2A"
    assert stored.class_type is ClassType.LAB
    assert db.scalars(select(Room)).one().room_type is RoomType.LAB


def test_time_slot_stores_times(db: Session) -> None:
    db.add(TimeSlot(day_of_week=0, start_time=time(8, 0), end_time=time(9, 30)))
    db.commit()

    slot = db.scalars(select(TimeSlot)).one()
    assert (slot.start_time, slot.end_time) == (time(8, 0), time(9, 30))
