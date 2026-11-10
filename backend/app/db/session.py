"""Silnik bazy danych i sesje SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()

if settings.is_sqlite:
    # SQLite w pamięci jest używany tylko w testach lokalnych – jedno współdzielone połączenie.
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Zależność FastAPI: jedna sesja na żądanie HTTP."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
