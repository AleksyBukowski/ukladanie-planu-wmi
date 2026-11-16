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
    COURSE ||--o{ ASSIGNMENT : "dotyczy"
    TEACHER ||--o{ ASSIGNMENT : "prowadzi"
    ASSIGNMENT ||--o{ ASSIGNMENT_GROUP : "obejmuje"
    STUDENT_GROUP ||--o{ ASSIGNMENT_GROUP : "uczestniczy"

    TIME_SLOT {
        int id PK
        int day_of_week "0 = pon, NOT NULL"
        time start_time "NOT NULL"
        time end_time "NOT NULL"
        enum week_type "all | odd | even"
    }
    ROOM {
        int id PK
        string code UK "NOT NULL"
        int capacity "NOT NULL"
        enum room_type "lecture_hall | classroom | lab"
    }
    STUDENT_GROUP {
        int id PK
        string code UK "NOT NULL"
        string name "NOT NULL"
        int size "NOT NULL"
    }
    TEACHER {
        int id PK
        string external_id UK "id z USOS"
        string title
        string first_name "NOT NULL"
        string last_name "NOT NULL"
    }
    COURSE {
        int id PK
        string code UK "NOT NULL"
        string name "NOT NULL"
    }
    ASSIGNMENT {
        int id PK
        int course_id FK "NOT NULL"
        int teacher_id FK "NOT NULL"
        enum class_type "lecture | exercises | lab"
        enum required_room_type "lecture_hall | classroom | lab"
        int units_per_week "NOT NULL"
    }
    ASSIGNMENT_GROUP {
        int assignment_id PK, FK
        int group_id PK, FK
    }
```

Kod: [`backend/app/models/domain.py`](../backend/app/models/domain.py).

Do dodania w kolejnych zadaniach: użytkownicy i role (FR-01, FR-02), niedostępności
prowadzących (FR-08), wersje planu i przydziały zajęć do terminów i sal (FR-11, FR-15),
uwagi recenzentów (FR-16).
