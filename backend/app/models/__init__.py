"""Wszystkie modele ORM.

Każdy nowy plik z modelami trzeba zaimportować tutaj – inaczej `Base.metadata.create_all`
nie utworzy jego tabel.
"""

from app.models.domain import (
    Assignment,
    ClassType,
    Course,
    Room,
    RoomType,
    StudentGroup,
    Teacher,
    TimeSlot,
)

__all__ = [
    "Assignment",
    "ClassType",
    "Course",
    "Room",
    "RoomType",
    "StudentGroup",
    "Teacher",
    "TimeSlot",
]
