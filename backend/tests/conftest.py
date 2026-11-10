import os

# Lokalnie testy działają na SQLite w pamięci – nie trzeba stawiać PostgreSQL.
# W CI zmienna DATABASE_URL wskazuje na prawdziwy PostgreSQL (usługa w GitHub Actions).
# Musi być ustawiona PRZED importem aplikacji, bo silnik bazy tworzony jest przy imporcie.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_database() -> Iterator[None]:
    """Każdy test dostaje pustą bazę."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
