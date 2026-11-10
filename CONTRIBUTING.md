# Zasady pracy w repozytorium

## Przepływ pracy

1. Weź zadanie z Jiry (np. `PLAN-12`) i przenieś je do „W toku”.
2. Utwórz gałąź od aktualnego `main`:
   ```bash
   git switch main && git pull
   git switch -c feature/PLAN-12-import-csv
   ```
   Prefiksy: `feature/` (nowa funkcja), `fix/` (błąd), `docs/`, `chore/` (konfiguracja, CI).
   **Klucz zadania w nazwie gałęzi** łączy ją z Jirą (GitHub for Jira).
3. Commituj małymi krokami. Wiadomość commita zaczynaj od klucza zadania:
   `PLAN-12: parser CSV dla sal`.
4. Przed pushem uruchom lokalnie te same sprawdzenia co CI (sekcja niżej).
5. Otwórz pull request do `main` z tytułem `PLAN-12: Krótki opis` i wypełnij szablon.
6. PR wymaga **zielonego CI i co najmniej jednej akceptacji**. Gałąź `main` jest chroniona –
   nie pushujemy do niej bezpośrednio.
7. Scalamy przez **Squash and merge**, potem usuwamy gałąź.

Limit pracy w toku: maksymalnie 2 zadania na osobę.

## Sprawdzenia przed pushem (to samo robi CI)

```bash
# Python (z katalogu głównego repo – wspólny ruff.toml)
ruff check . && ruff format --check .
cd backend && pytest
cd ../mock-usos && pytest

# Frontend
cd frontend
npm run lint && npm run format:check && npm run build
```

Automatyczne poprawki formatowania: `ruff format .` oraz `npm run format`.

W kontenerach: `docker compose exec backend pytest`, `docker compose exec frontend npm run lint`.

## Konwencje

- **Język:** identyfikatory w kodzie po angielsku; komentarze, docstringi, UI i dokumentacja po polsku.
- **API:** wszystkie endpointy pod `/api/...`; nowy moduł = plik w `backend/app/api/routes/`
  zarejestrowany w `backend/app/api/router.py`. Logika trafia do `backend/app/services/`,
  żeby dało się ją testować bez HTTP.
- **Modele:** nowe modele importujemy w `backend/app/models/__init__.py`. Zmiana istniejącej
  tabeli wymaga odtworzenia bazy (`docker compose down -v`) – zaznacz to w opisie PR.
- **Frontend:** widoki w `frontend/src/pages/`, podpinane w `frontend/src/router.tsx`;
  zapytania do API przez `frontend/src/api/client.ts`. Komponenty z Mantine zamiast własnego CSS.
- **Testy:** każda zmiana logiki walidacji kolizji i solvera ma testy w pytest (NFR-07).
- **Dane:** tylko dane syntetyczne. Pliki z prawdziwymi danymi trzymaj w `data/private/`
  (ignorowany przez git).
- **Sekrety:** nigdy w repozytorium – tylko w `.env` (ignorowany) i w ustawieniach serwera.

## Definition of Done

Kod po review i scalony do `main`, CI zielone, testy przechodzą, dokumentacja zaktualizowana,
funkcja sprawdzona na stagingu przez inną osobę niż autor.
