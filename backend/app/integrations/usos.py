"""Klient (zamockowanego) USOS – wyłącznie odczyt (NFR-05).

Prawdziwe USOS API jest poza zakresem MVP; w środowisku deweloperskim adres
`USOS_BASE_URL` wskazuje na serwis `mock-usos`, który udostępnia pliki eksportu
z katalogu `data/usos-export/`.
"""

import httpx

from app.core.config import get_settings


class UsosClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._base_url = (base_url or get_settings().usos_base_url).rstrip("/")
        self._timeout = timeout

    def list_exports(self) -> list[str]:
        """Nazwy dostępnych plików eksportu (np. `rooms.csv`)."""
        response = httpx.get(f"{self._base_url}/exports", timeout=self._timeout)
        response.raise_for_status()
        return response.json()["files"]

    def download_export(self, name: str) -> bytes:
        """Zawartość pliku eksportu – do przekazania parserowi importu."""
        response = httpx.get(f"{self._base_url}/exports/{name}", timeout=self._timeout)
        response.raise_for_status()
        return response.content
