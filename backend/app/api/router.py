"""Główny router API – tu rejestrujemy routery poszczególnych modułów.

Nowy moduł: utwórz `app/api/routes/<nazwa>.py` z `router = APIRouter(prefix="/<nazwa>")`
i dodaj go poniżej.
"""

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
