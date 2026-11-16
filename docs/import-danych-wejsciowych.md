# Import danych wejściowych (FR-04, FR-05, część D-03)

Import wczytuje dane, z których powstaje plan: sale, grupy, prowadzących, przedmioty i
przypisania prowadzący–przedmiot–grupa. Pliki pochodzą z eksportu USOS albo z szablonu
wypełnionego w dziekanacie.

Siatkę godzin importuje się osobno – patrz [`import-siatki-godzin.md`](import-siatki-godzin.md).

## Pliki

Import wymaga **kompletu pięciu plików** w jednym żądaniu. Tylko tak da się sprawdzić, czy
przypisania odwołują się do istniejących przedmiotów, prowadzących i grup.

| Plik          | Kolumny                                                                        |
| ------------- | ------------------------------------------------------------------------------ |
| `rooms`       | `code`, `capacity`, `room_type`                                                |
| `groups`      | `code`, `name`, `size`                                                         |
| `teachers`    | `external_id`, `title` (opcjonalna), `first_name`, `last_name`                 |
| `courses`     | `code`, `name`                                                                 |
| `assignments` | `course_code`, `teacher_external_id`, `group_code`, `class_type`, `required_room_type`, `units_per_week` |

Przykładowe pliki: [`data/usos-export/`](../data/usos-export/).

Zasady plików (CSV/XLSX, kodowanie, separator, nagłówek, puste wiersze, limit 5 MB) są takie
same jak przy siatce godzin – patrz sekcja „Zasady pliku” w
[`import-siatki-godzin.md`](import-siatki-godzin.md).

## Reguły walidacji

**Wartości w wierszach**

| Kolumna                                  | Reguła                                                  |
| ---------------------------------------- | ------------------------------------------------------- |
| wszystkie poza `title`                   | wartość wymagana                                        |
| `capacity`, `size`                       | liczba całkowita 1–10 000                               |
| `units_per_week`                         | liczba całkowita 1–50 (liczba bloków w tygodniu)        |
| `room_type`, `required_room_type`        | `lecture_hall`, `classroom` albo `lab`                  |
| `class_type`                             | `lecture`, `exercises` albo `lab`                       |
| kody grup i sal                          | najwyżej 32 znaki                                       |
| kody przedmiotów, `external_id`, `title` | najwyżej 64 znaki                                       |
| nazwy przedmiotów i grup                 | najwyżej 200 znaków                                     |
| imię, nazwisko                           | najwyżej 100 znaków                                     |

Wielkość liter w wartościach słownikowych nie ma znaczenia (`Lab` = `lab`).

**Unikalność.** W obrębie pliku nie mogą się powtarzać: kod sali, kod grupy, `external_id`
prowadzącego, kod przedmiotu.

**Spójność referencji.** Każde przypisanie musi wskazywać przedmiot (`course_code`),
prowadzącego (`teacher_external_id`) i grupę (`group_code`) z pozostałych plików.

**Pojemność sal (FR-07).** Dla każdego przypisania musi istnieć co najmniej jedna sala
wymaganego typu, w której zmieści się grupa. Ta reguła jest sprawdzana tylko wtedy, gdy pliki
sal i grup nie mają żadnych błędów – inaczej wynik byłby mylący.

## Co się dzieje przy imporcie

Import **zastępuje wszystkie dotychczasowe dane wejściowe** (sale, grupy, prowadzących,
przedmioty, przypisania). Siatka godzin pozostaje bez zmian.

Import wykonuje się w całości albo wcale (FR-05, NFR-05): przy jakimkolwiek błędzie – w danych
albo podczas zapisu do bazy – nic się nie zmienia.

Błędy są zbierane ze wszystkich plików naraz. Wyjątek: błędy pojemności pojawią się dopiero
po poprawieniu błędów w plikach sal i grup. Raport ma najwyżej 1000 pozycji.

## Raport błędów

Przy błędach API zwraca kod `422`. Każdy błąd ma plik (`file`), numer wiersza w pliku (`row`,
nagłówek to zwykle wiersz 1) i kolumnę (`column`):

```json
{
  "detail": "Import odrzucony – popraw błędy i wgraj pliki ponownie.",
  "errors": [
    {
      "file": "rooms",
      "row": 32,
      "column": "code",
      "message": "Wartość „A0.01” powtarza się – występuje już w wierszu 2."
    },
    {
      "file": "groups",
      "row": 3,
      "column": "size",
      "message": "„dwadzieścia” nie jest liczbą całkowitą."
    },
    {
      "file": "assignments",
      "row": 5,
      "column": "teacher_external_id",
      "message": "„T999” nie występuje w pliku prowadzących."
    }
  ]
}
```

Błąd dotyczący całego pliku (brak pliku, brak kolumny, nieobsługiwany format) ma
`"row": null` i `"column": null`.

## Dla programistów

- Endpoint: `POST /api/imports`, pola formularza `rooms`, `groups`, `teachers`, `courses`,
  `assignments`. Odpowiedź 200: liczba zapisanych rekordów każdego rodzaju.
- Walidacja i zapis: `backend/app/services/data_import.py` (opis plików w `SPECS`).
- Parser CSV/XLSX: `backend/app/services/tabular.py`.
