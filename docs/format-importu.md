# Specyfikacja formatu importu (D-03)

| | |
| --- | --- |
| **Wersja** | 1.0 (20.11.2026) |
| **Wymagania** | FR-03, FR-04, FR-05, FR-07, NFR-04, NFR-05 |
| **Szablony** | [`data/templates/`](../data/templates/) (CSV i XLSX) |
| **Przykładowy zbiór** | [`data/usos-export/`](../data/usos-export/) (D-10, dane syntetyczne) |

Dokument opisuje pliki, z których system buduje dane wejściowe planu: jakie są pliki, jakie
mają kolumny, jakie wartości są dozwolone i co się dzieje, gdy dane są błędne. Pliki pochodzą
z eksportu USOS albo z szablonu wypełnionego ręcznie w dziekanacie.

Szczegóły techniczne dla programistów (endpointy, kody odpowiedzi) są w sekcji 7.

## 1. Zestawy importu

System ma dwa niezależne importy:

| Import | Pliki | Ekran | Co zastępuje |
| --- | --- | --- | --- |
| **Siatka godzin** (FR-03) | `time_slots` | *Siatka godzin* | całą siatkę godzin |
| **Dane wejściowe** (FR-04) | `rooms`, `groups`, `teachers`, `courses`, `assignments` – **komplet pięciu plików** | *Import danych* | wszystkie sale, grupy, prowadzących, przedmioty i przypisania |

Dane wejściowe wgrywa się zawsze kompletem, bo tylko wtedy da się sprawdzić, czy przypisania
odwołują się do istniejących przedmiotów, prowadzących i grup. Import danych wejściowych nie
zmienia siatki godzin i odwrotnie.

## 2. Zasady wspólne dla wszystkich plików

| Zasada | Opis |
| --- | --- |
| Format | `.csv` albo `.xlsx`. Stary format `.xls` nie jest obsługiwany – zapisz plik jako `.xlsx`. |
| Arkusz (XLSX) | Czytany jest **pierwszy arkusz**. Formuły są czytane jako ostatnio obliczone wartości. |
| Kodowanie (CSV) | UTF-8 (także z BOM) albo Windows-1250. Zalecane: UTF-8. |
| Separator (CSV) | przecinek `,`, średnik `;` albo tabulator – rozpoznawany automatycznie z nagłówka (polski Excel zapisuje CSV ze średnikiem). Wartość zawierającą separator ujmij w cudzysłów: `"Informatyka, rok 2"`. |
| Nagłówek | Pierwszy niepusty wiersz. Nazwy kolumn jak w tabelach poniżej; wielkość liter i spacje na brzegach nie mają znaczenia, kolejność kolumn jest dowolna. |
| Dodatkowe kolumny | Ignorowane (można zostawić np. kolumnę z uwagami). |
| Puste wiersze | Pomijane. |
| Spacje | Usuwane z początku i końca każdej wartości. Pusta komórka = brak wartości. |
| Rozmiar | Najwyżej 5 MB i 50 000 wierszy danych na plik. |
| Numer wiersza | W raporcie błędów taki, jak widać w Excelu (nagłówek to zwykle wiersz 1). |

## 3. Siatka godzin – `time_slots`

Każdy wiersz to jeden blok zajęciowy w tygodniu. Zajęcia mogą być przydzielane tylko do tych
bloków. Szczegółowy opis: [`import-siatki-godzin.md`](import-siatki-godzin.md).

| Kolumna | Wymagana | Typ | Opis i dozwolone wartości |
| --- | --- | --- | --- |
| `day_of_week` | tak | dzień | `0`–`6` (`0` = poniedziałek) albo nazwa dnia: `poniedziałek`/`pon`/`pn`, `wtorek`/`wt`, `środa`/`śr`, `czwartek`/`czw`/`cz`, `piątek`/`pt`, `sobota`/`sob`, `niedziela`/`nd` |
| `start_time` | tak | godzina | `GG:MM`, np. `08:00` (także `8.00` albo komórka czasu w XLSX) |
| `end_time` | tak | godzina | jw.; musi być późniejsza niż `start_time` |

**Reguły:** bloki tego samego dnia nie mogą na siebie nachodzić (stykanie się, np. koniec
09:30 i początek 09:30, jest dozwolone); plik musi zawierać co najmniej jeden blok.

## 4. Dane wejściowe

### 4.1 Sale – `rooms`

| Kolumna | Wymagana | Typ | Opis i dozwolone wartości |
| --- | --- | --- | --- |
| `code` | tak | tekst ≤ 32 | Oznaczenie sali, np. `A1.12`. **Unikalne** w pliku. |
| `capacity` | tak | liczba całkowita 1–10 000 | Liczba miejsc. |
| `room_type` | tak | słownik | `lecture_hall` (sala wykładowa), `classroom` (sala ćwiczeniowa), `lab` (pracownia / laboratorium) |

### 4.2 Grupy – `groups`

| Kolumna | Wymagana | Typ | Opis i dozwolone wartości |
| --- | --- | --- | --- |
| `code` | tak | tekst ≤ 32 | Kod grupy zajęciowej, np. `INF-2A`. **Unikalny** w pliku. |
| `name` | tak | tekst ≤ 200 | Nazwa opisowa, np. `Informatyka, rok 2, grupa A`. |
| `size` | tak | liczba całkowita 1–10 000 | Liczebność grupy. |

> **NFR-04:** plik grup zawiera wyłącznie kod, nazwę i liczebność. **Nie wolno** dodawać list
> studentów, numerów albumów ani innych danych osobowych studentów.

### 4.3 Prowadzący – `teachers`

| Kolumna | Wymagana | Typ | Opis i dozwolone wartości |
| --- | --- | --- | --- |
| `external_id` | tak | tekst ≤ 64 | Identyfikator prowadzącego (np. z USOS). **Unikalny** w pliku; po nim przypisania wskazują prowadzącego. |
| `title` | nie | tekst ≤ 64 | Tytuł/stopień, np. `dr`, `dr hab.`, `prof.`. |
| `first_name` | tak | tekst ≤ 100 | Imię. |
| `last_name` | tak | tekst ≤ 100 | Nazwisko. |

> Przechowujemy tylko dane potrzebne do planu (NFR-04): bez e-maili, telefonów, numerów PESEL.

### 4.4 Przedmioty – `courses`

| Kolumna | Wymagana | Typ | Opis i dozwolone wartości |
| --- | --- | --- | --- |
| `code` | tak | tekst ≤ 64 | Kod przedmiotu, np. `ASD`. **Unikalny** w pliku. |
| `name` | tak | tekst ≤ 200 | Nazwa przedmiotu. |

### 4.5 Przypisania – `assignments`

Każdy wiersz to zajęcia do rozplanowania: kto, czego, z kim, w jakiej formie i ile razy w
tygodniu.

| Kolumna | Wymagana | Typ | Opis i dozwolone wartości |
| --- | --- | --- | --- |
| `course_code` | tak | odwołanie | `code` z pliku `courses`. |
| `teacher_external_id` | tak | odwołanie | `external_id` z pliku `teachers`. |
| `group_code` | tak | odwołanie | `code` z pliku `groups`. **Zajęcia łączone** (np. wykład dla kilku grup): kody rozdzielone pionową kreską, np. `INF-2A\|INF-2B\|INF-2C`. |
| `class_type` | tak | słownik | `lecture` (wykład), `exercises` (ćwiczenia), `lab` (laboratorium) |
| `required_room_type` | tak | słownik | `lecture_hall`, `classroom`, `lab` – jak w `rooms.room_type` |
| `units_per_week` | tak | liczba całkowita 1–50 | Liczba bloków siatki w tygodniu, np. `2` = dwa osobne bloki. |

Typowe zestawienia formy zajęć i typu sali: `lecture` → `lecture_hall`, `exercises` →
`classroom`, `lab` → `lab`. System ich nie wymusza – np. ćwiczenia w pracowni są dozwolone.

**Zajęcia łączone.** Wiersz z kilkoma grupami to *jedne* zajęcia: odbywają się w tym samym
terminie i sali dla wszystkich wymienionych grup, a sala musi pomieścić **sumę** ich liczebności.
Tak należy zapisywać wspólne wykłady dla roku – zamiast osobnego wiersza dla każdej grupy.

## 5. Wartości słownikowe

Wielkość liter nie ma znaczenia (`Lab` = `lab`).

| Słownik | Wartość | Znaczenie |
| --- | --- | --- |
| typ sali | `lecture_hall` | sala wykładowa |
| | `classroom` | sala ćwiczeniowa |
| | `lab` | pracownia komputerowa / laboratorium |
| forma zajęć | `lecture` | wykład |
| | `exercises` | ćwiczenia |
| | `lab` | laboratorium |

## 6. Walidacja i raport błędów

Import wykonuje się **w całości albo wcale** (FR-05, NFR-05). Najpierw sprawdzane są wszystkie
pliki; jeśli jest choć jeden błąd, nic nie zostaje zapisane, a planista dostaje pełną listę
błędów. Poprawny import **zastępuje** dotychczasowe dane danego zestawu.

Kolejność sprawdzania:

1. **Plik** – format, nagłówek, obecność wymaganych kolumn, komplet pięciu plików danych wejściowych.
2. **Wiersz** – wymagane wartości, typy liczb, zakresy, wartości słownikowe, długość tekstu,
   unikalność kluczy w pliku.
3. **Między plikami** – czy przedmiot, prowadzący i każda grupa z przypisania istnieją w
   pozostałych plikach (spójność referencji).
4. **Pojemność (FR-07)** – czy dla każdego przypisania istnieje co najmniej jedna sala
   wymaganego typu, która pomieści grupę (przy zajęciach łączonych: sumę grup). Sprawdzane
   tylko wtedy, gdy pliki sal i grup nie mają błędów – inaczej wynik byłby mylący.

Każdy błąd w raporcie ma: **plik**, **numer wiersza**, **kolumnę** i **opis**. Błąd dotyczący
całego pliku (brak pliku, brak kolumny, zły format) nie ma wiersza ani kolumny. Raport ma
najwyżej 1000 pozycji.

Przykłady:

| Plik | Wiersz | Kolumna | Opis |
| --- | --- | --- | --- |
| `rooms` | 32 | `code` | Wartość „A0.01” powtarza się – występuje już w wierszu 2. |
| `groups` | 3 | `size` | „dwadzieścia” nie jest liczbą całkowitą. |
| `assignments` | 5 | `teacher_external_id` | „T999” nie występuje w pliku prowadzących. |
| `assignments` | 9 | `group_code` | Żadna sala typu `lecture_hall` nie pomieści 150 osób. |
| `teachers` | – | – | Brak wymaganych kolumn: first_name. |

## 7. Dla programistów

| Import | Endpoint | Pola formularza (`multipart/form-data`) | Odpowiedź 200 |
| --- | --- | --- | --- |
| Siatka godzin | `POST /api/time-slots/import` | `file` | `{ imported, time_slots[] }` |
| Dane wejściowe | `POST /api/imports` | `rooms`, `groups`, `teachers`, `courses`, `assignments` | `{ rooms, groups, teachers, courses, assignments }` (liczby zapisanych rekordów) |

Błędy danych: `422` z ciałem `{ "detail": "...", "errors": [{ "file", "row", "column", "message" }] }`
(`file` jest pusty przy imporcie jednego pliku). Za duży plik: `413`.

Implementacja: parser CSV/XLSX `backend/app/services/tabular.py`, siatka
`backend/app/services/time_grid.py`, dane wejściowe `backend/app/services/data_import.py`
(gałąź SCRUM-22).

**Stan implementacji (20.11.2026):** siatka godzin – zgodna ze specyfikacją. Dane wejściowe –
SCRUM-22 realizuje sekcje 4–6 z wyjątkiem **zajęć łączonych** (wiele kodów w `group_code`,
suma liczebności w regule pojemności), które trzeba dodać przy dostosowaniu importu do relacji
M:N `Assignment.groups` z SCRUM-19.

## 8. Odwzorowanie eksportu USOS

Nie mamy dostępu do USOS API, więc dane z USOS trafiają do systemu przez pliki zgodne z tą
specyfikacją (w środowisku deweloperskim udaje je serwis `mock-usos`). Przy przygotowaniu
eksportu w dziekanacie:

| Plik | Źródło w USOS |
| --- | --- |
| `rooms` | sale dydaktyczne wydziału (oznaczenie, liczba miejsc); typ sali uzupełnia dziekanat |
| `groups` | grupy zajęciowe cyklu dydaktycznego – tylko kod, nazwa i liczba studentów |
| `teachers` | prowadzący grup – identyfikator osoby, tytuł, imię, nazwisko |
| `courses` | przedmioty realizowane w semestrze (kod, nazwa) |
| `assignments` | zajęcia grup z prowadzącym i formą zajęć; liczbę bloków w tygodniu i wymagany typ sali uzupełnia dziekanat |

Pola, których brakuje w eksporcie USOS (typ sali, `units_per_week`, `required_room_type`),
dziekanat uzupełnia w szablonie XLSX przed importem (ryzyko R-01).

## Historia zmian

| Wersja | Data | Zmiany |
| --- | --- | --- |
| 1.0 | 20.11.2026 | Pierwsza wersja: siatka godzin, pięć plików danych wejściowych, reguły walidacji, zajęcia łączone. |
