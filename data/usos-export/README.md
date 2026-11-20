# Zbiór referencyjny (D-10) – syntetyczny eksport z USOS

Pliki w tym katalogu udają eksport danych z USOS dla jednego semestru. Są serwowane przez
serwis `mock-usos` (`http://localhost:8001/exports`) i służą do testów importu i solvera.

**Tylko dane syntetyczne** (NFR-04) – imiona i nazwiska są losowane ze słownika i mają
sztuczny sufiks, a grupy mają tylko kod, nazwę i liczebność. Prawdziwe lub zanonimizowane
pliki trzymaj lokalnie w `data/private/` (katalog jest w `.gitignore`).

Format plików opisuje specyfikacja importu: [`docs/format-importu.md`](../../docs/format-importu.md) (D-03).

## Zawartość

| Plik | Rekordów |
| --- | --- |
| `rooms.csv` | 30 sal (6 wykładowych, 12 ćwiczeniowych, 12 pracowni) |
| `teachers.csv` | 100 prowadzących |
| `courses.csv` | 40 przedmiotów |
| `groups.csv` | 48 grup (4 kierunki × 3 lata × 4 grupy) |
| `assignments.csv` | 600 przypisań |

## Generowanie

```bash
python data/usos-export/generate_synthetic_data.py
```

Skrypt używa tylko biblioteki standardowej i stałego ziarna losowości (`random.seed(42)`),
więc za każdym razem tworzy te same pliki. Nadpisuje pliki CSV w tym katalogu.

## Znane ograniczenia

- Przypisania są losowane niezależnie, więc obciążenie grup jest nierówne (6–21 zajęć
  tygodniowo), a część przypisań się powtarza.
- Wykłady są przypisane do pojedynczych grup (bez zajęć łączonych) – 209 wykładów na 6 sal
  wykładowych prawie wypełnia siatkę 5 dni × 7 bloków, więc solver może nie znaleźć planu bez
  kolizji. Do poprawy w generatorze: wspólne wykłady dla roku (`group_code` z kilkoma grupami).
