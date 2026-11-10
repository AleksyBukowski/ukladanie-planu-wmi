# syntax=docker/dockerfile:1

# --- Wspólna baza: zależności uruchomieniowe ---
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN useradd --create-home --uid 1000 appuser

# --- Tryb deweloperski: + pytest/ruff, hot reload (używany przez docker-compose.override.yml) ---
FROM base AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- Produkcja (domyślny target) ---
FROM base AS prod
COPY app ./app
USER appuser
EXPOSE 8000
# Jeden worker: tabele są tworzone przy starcie (create_all), a solver i tak działa w osobnym procesie.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
