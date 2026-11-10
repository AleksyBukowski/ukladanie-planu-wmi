# Architektura (D-04, wersja wstępna)

## Kontenery (C4, poziom II)

```mermaid
flowchart LR
    user["Planista / Recenzent / Student<br/>(przeglądarka)"]

    subgraph compose["Docker Compose"]
        fe["frontend<br/>React + Mantine<br/>(dev: Vite · prod: nginx)"]
        be["backend<br/>FastAPI + SQLAlchemy<br/>solver OR-Tools"]
        db[("db<br/>PostgreSQL 16")]
        usos["mock-usos<br/>eksport USOS<br/>(tylko odczyt)"]
    end

    files[/"data/usos-export/<br/>CSV/XLSX (syntetyczne)"/]

    user -->|HTTPS| fe
    fe -->|"/api/* (proxy)"| be
    be -->|SQL| db
    be -->|"HTTP GET (odczyt)"| usos
    usos --- files
```

- Frontend wywołuje wyłącznie względne ścieżki `/api/*`; w dev przekierowuje je Vite,
  w produkcji nginx. Dzięki temu nie potrzebujemy CORS ani konfiguracji adresu API.
- Prawdziwe USOS API jest poza zakresem MVP. `mock-usos` udaje źródło eksportu – backend
  może pobrać z niego plik i przekazać go temu samemu parserowi co ręczny upload (FR-04).
- Solver działa w backendzie, w osobnym procesie z limitem czasu (FR-11).

## Model danych (stan początkowy)

```mermaid
erDiagram
    COURSE ||--o{ ASSIGNMENT : "przedmiot"
    TEACHER ||--o{ ASSIGNMENT : "prowadzi"
    STUDENT_GROUP ||--o{ ASSIGNMENT : "uczestniczy"

    TIME_SLOT {
        int day_of_week "0 = pon"
        time start_time
        time end_time
    }
    ROOM {
        string code UK
        int capacity
        enum room_type "lecture_hall | classroom | lab"
    }
    STUDENT_GROUP {
        string code UK
        string name
        int size
    }
    TEACHER {
        string external_id UK "id z USOS"
        string title
        string first_name
        string last_name
    }
    COURSE {
        string code UK
        string name
    }
    ASSIGNMENT {
        enum class_type "lecture | exercises | lab"
        enum required_room_type
        int units_per_week
    }
```

Kod: [`backend/app/models/domain.py`](../backend/app/models/domain.py).

Do dodania w kolejnych zadaniach: użytkownicy i role (FR-01, FR-02), niedostępności
prowadzących (FR-08), wersje planu i przydziały zajęć do terminów i sal (FR-11, FR-15),
uwagi recenzentów (FR-16).
