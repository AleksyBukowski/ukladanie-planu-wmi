# System układania planu zajęć – WMiI UAM

Aplikacja webowa wspierająca planistę dziekanatu: import danych, automatyczne generowanie
propozycji planu (OR-Tools CP-SAT), ręczna korekta z wykrywaniem kolizji, wersje planu,
eksport CSV/XLSX i publiczny widok planu.

| Warstwa      | Technologia                                   | Katalog       |
| ------------ | --------------------------------------------- | ------------- |
| Frontend     | React + TypeScript, Vite, Mantine UI          | `frontend/`   |
| Backend      | Python 3.12, FastAPI, SQLAlchemy, openpyxl    | `backend/`    |
| Solver       | Google OR-Tools (CP-SAT)                      | `backend/app/solver/` |
| Baza danych  | PostgreSQL 16                                 | –             |
| Mock USOS    | FastAPI, serwuje syntetyczny eksport (tylko odczyt) | `mock-usos/`, `data/usos-export/` |
| Uruchomienie | Docker Compose, CI w GitHub Actions           | `docker-compose*.yml`, `.github/` |

## Szybki start (Docker – zalecane)

Wymagany jest tylko [Docker Desktop](https://www.docker.com/products/docker-desktop/) (lub Docker Engine + Compose v2.24+).

```bash
git clone https://github.com/AleksyBukowski/ukladanie-planu-wmi.git
cd ukladanie-planu-wmi
docker compose up --build
```

| Usługa         | Adres                               |
| -------------- | ----------------------------------- |
| Frontend       | http://localhost:5173               |
| API – Swagger  | http://localhost:8000/api/docs      |
| Mock USOS      | http://localhost:8001/exports       |
| PostgreSQL     | `localhost:5432`, baza/login/hasło: `plan` |

Kod backendu, frontendu i mock USOS jest montowany do kontenerów – zmiany przeładowują się
automatycznie. Plik `.env` nie jest wymagany; aby zmienić porty lub hasła, skopiuj
`.env.example` do `.env`.

Przydatne polecenia:

```bash
docker compose exec backend pytest            # testy backendu w kontenerze
docker compose exec backend ruff check .      # lint backendu
docker compose logs -f backend                # logi jednej usługi
docker compose down                           # zatrzymanie
docker compose down -v                        # zatrzymanie + usunięcie bazy
```

> **Nowa zależność npm/pip?** Po zmianie `package.json` lub `requirements*.txt` przebuduj obrazy:
> `docker compose up --build` (dla frontendu dodatkowo `-V`, żeby odświeżyć wolumen `node_modules`).

### Zmiany w modelu danych

W MVP nie używamy migracji (decyzja z dokumentu wymagań, sekcja 1.1) – tabele są tworzone
przy starcie backendu (`Base.metadata.create_all`). `create_all` **nie modyfikuje istniejących
tabel**, więc po zmianie istniejącego modelu odtwórz bazę: `docker compose down -v && docker compose up`.

## Praca bez Dockera (opcjonalnie)

**Backend** – Python 3.12 lub 3.13 (OR-Tools nie ma jeszcze paczek dla nowszych wersji):

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows;  Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                          # testy na SQLite w pamięci – PostgreSQL niepotrzebny
uvicorn app.main:app --reload   # wymaga PostgreSQL, np.: docker compose up db
```

**Frontend** – Node.js 22 LTS:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, /api przekierowywane na localhost:8000
npm run lint && npm run format:check && npm run build
```

## Wdrożenie na serwer

Na serwerze uruchamiamy samą konfigurację bazową (bez `docker-compose.override.yml`):
frontend jest budowany i serwowany przez nginx, który przekierowuje `/api` do backendu.

```bash
cp .env.example .env    # ustaw SECRET_KEY, POSTGRES_PASSWORD, HTTP_PORT
docker compose -f docker-compose.yml up -d --build
```

Aplikacja nasłuchuje na `HTTP_PORT` (domyślnie 8080); HTTPS zapewnia reverse proxy serwera (NFR-03).

## Struktura repozytorium

```
backend/
  app/
    api/routes/     endpointy REST (cienkie – logika w services/)
    core/           konfiguracja ze zmiennych środowiskowych
    db/             silnik, sesje, klasa bazowa ORM
    models/         modele SQLAlchemy (nowe modele zaimportuj w models/__init__.py)
    schemas/        schematy Pydantic (wejście/wyjście API)
    services/       logika: import, walidacja kolizji, eksport
    solver/         generowanie planu (OR-Tools)
    integrations/   klient mock USOS
  tests/            pytest
frontend/src/
  api/              klient HTTP
  components/       współdzielone komponenty
  layout/           AppShell (nagłówek + menu)
  pages/            widoki (podpinane w router.tsx)
mock-usos/          zamockowany USOS
data/usos-export/   syntetyczne pliki eksportu serwowane przez mock USOS
docs/               dokumentacja projektu, notatki ze spotkań
```

## Zasady pracy

Gałęzie, pull requesty, konwencje i CI – patrz [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencja i dane

Kod źródłowy i dokumentacja pozostają do dyspozycji WMiI UAM. W repozytorium są wyłącznie
dane syntetyczne – prawdziwe dane osobowe nie mogą trafić do repozytorium (NFR-04).
