"""Konfiguracja aplikacji wczytywana ze zmiennych środowiskowych (NFR-06)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://plan:plan@localhost:5432/plan"
    secret_key: str = "change-me-in-production"
    usos_base_url: str = "http://localhost:8001"

    # Prefiks wszystkich endpointów – frontend i reverse proxy kierują /api/* do backendu.
    api_prefix: str = "/api"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
