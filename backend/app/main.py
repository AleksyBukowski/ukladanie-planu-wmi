from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  – rejestruje modele w Base.metadata
from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # MVP bez migracji (decyzja z dokumentu wymagań, sekcja 1.1): tabele tworzone przy starcie.
    # Alembic dodamy, gdy w bazie pojawią się dane, których nie da się odtworzyć.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="System układania planu zajęć WMiI UAM",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

app.include_router(api_router, prefix=settings.api_prefix)
