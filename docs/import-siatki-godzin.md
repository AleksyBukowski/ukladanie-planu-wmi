# Import siatki godzin (FR-03, część D-03)

Siatka godzin to lista bloków zajęciowych w tygodniu, np. „poniedziałek 08:00–09:30”.
Solver i ręczna edycja planu przydzielają zajęcia wyłącznie do tych bloków.

Siatkę można wczytać z pliku CSV lub XLSX albo ustawić ręcznie przez API
(Swagger: `/api/docs`, sekcja „siatka godzin”).

> Ten dokument opisuje tylko plik siatki. Format plików z salami, grupami, prowadzącymi
> i przypisaniami opisuje specyfikacja importu (D-03).

## Szablon pliku

Pierwszy niepusty wiersz to nagłówek, każdy kolejny wiersz to jeden blok:

```csv
day_of_week,start_time,end_time
poniedziałek,08:00,09:30
poniedziałek,09:45,11:15
poniedziałek,11:30,13:00
wtorek,08:00,09:30
```

| Kolumna       | Wymagana | Wartości                                                                 |
| ------------- | -------- | ------------------------------------------------------------------------ |
| `day_of_week` | tak      | liczba `0`–`6` (`0` = poniedziałek, `6` = niedziela) albo nazwa dnia     |
| `start_time`  | tak      | godzina rozpoczęcia, np. `08:00`                                         |
| `end_time`    | tak      | godzina zakończenia, późniejsza niż rozpoczęcie                          |

**Nazwy dni.** Wielkość liter i polskie znaki nie mają znaczenia, kropka na końcu jest pomijana.

| Dzień        | Akceptowane zapisy                     |
| ------------ | -------------------------------------- |
| poniedziałek | `0`, `poniedziałek`, `pon`, `pn`       |
| wtorek       | `1`, `wtorek`, `wt`                    |
| środa        | `2`, `środa`, `śr`                     |
| czwartek     | `3`, `czwartek`, `czw`, `cz`           |
| piątek       | `4`, `piątek`, `pt`, `pią`             |
| sobota       | `5`, `sobota`, `sob`, `so`             |
| niedziela    | `6`, `niedziela`, `niedz`, `nd`, `nie` |

Działają też nazwy angielskie (`monday`, `mon` itd.).

**Godziny.** Akceptowane formaty: `8:00`, `08:00`, `8.00`, `08:00:00`. W pliku XLSX może to
być też komórka sformatowana jako czas.

## Zasady pliku

- **Formaty.** Obsługiwane są pliki `.csv` i `.xlsx`. Stary format `.xls` nie jest obsługiwany;
  zapisz plik ponownie jako `.xlsx`. Maksymalny rozmiar pliku to 5 MB.
- **CSV.** Kodowanie UTF-8 albo Windows-1250. Separatorem może być przecinek, średnik
  (domyślny w polskim Excelu) albo tabulator; rozpoznawany jest po wierszu nagłówka.
- **XLSX.** Czytany jest tylko pierwszy arkusz.
- **Nagłówek.** Kolejność kolumn jest dowolna, wielkość liter nie ma znaczenia.
  Dodatkowe kolumny (np. `uwagi`) są pomijane.
- **Puste wiersze** są pomijane.

## Reguły siatki

- Bloki tego samego dnia **nie mogą na siebie nachodzić**.
- Bloki mogą się stykać: `08:00–09:30` i `09:30–11:00` to poprawna siatka.
- Plik musi zawierać co najmniej jeden blok.

## Co się dzieje przy imporcie

Import **zastępuje całą dotychczasową siatkę** zawartością pliku.

Import wykonuje się w całości albo wcale (FR-05). Jeśli w pliku jest choć jeden błąd,
nic nie zostaje zapisane, a obecna siatka pozostaje bez zmian.

Plik jest sprawdzany w dwóch krokach:

1. **Wartości w wierszach:** brakujące komórki, nieznane dni, błędne godziny, koniec bloku
   nie późniejszy niż początek. Zgłaszane są wszystkie takie błędy naraz.
2. **Nakładanie się bloków.** Ten krok wykonuje się dopiero wtedy, gdy wszystkie wiersze
   przeszły krok 1. Po poprawieniu błędów z kroku 1 kolejny import może więc zgłosić jeszcze
   błędy nakładania.

## Raport błędów

Przy błędach API zwraca kod `422` z listą błędów. `row` to numer wiersza w pliku (nagłówek to
zwykle wiersz 1, tak jak w Excelu), a `column` to nazwa kolumny.

Na przykład dla pliku:

```csv
day_of_week,start_time,end_time
pon,08:00,09:30
funday,08:00,09:30
wt,11:00,10:00
```

odpowiedź wygląda tak:

```json
{
  "detail": "Plik siatki godzin zawiera błędy.",
  "errors": [
    {
      "row": 3,
      "column": "day_of_week",
      "message": "Nieprawidłowy dzień tygodnia „funday” – podaj liczbę 0–6 (0 = poniedziałek) lub nazwę dnia, np. „poniedziałek”, „pon”."
    },
    {
      "row": 4,
      "column": "end_time",
      "message": "Godzina zakończenia musi być późniejsza niż godzina rozpoczęcia."
    }
  ]
}
```

Błąd dotyczący całego pliku, np. brak wymaganej kolumny albo nieobsługiwany format, ma
`"row": null` i `"column": null`.

Nakładające się bloki są zgłaszane przy późniejszym z nich, z numerem wiersza bloku, na który
nachodzi, np. „Blok poniedziałek 09:00–10:30 nachodzi na blok z wiersza 2 (08:00–09:30).”

## Dla programistów

- Endpoint: `POST /api/time-slots/import` (pole formularza `file`).
- Logika importu i walidacji: `backend/app/services/time_grid.py`.
- Wspólny parser CSV/XLSX, z którego mogą korzystać importy innych encji:
  `backend/app/services/tabular.py`.
