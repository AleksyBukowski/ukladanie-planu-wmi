# Szablony plików importu (D-03)

Puste szablony z nagłówkiem i przykładowymi wierszami – do wypełnienia w dziekanacie albo
jako wzór eksportu z USOS. Każdy plik jest w dwóch wersjach: `.csv` (UTF-8) i `.xlsx`.

| Plik | Import | Ekran |
| --- | --- | --- |
| `time_slots` | siatka godzin | *Siatka godzin* |
| `rooms`, `groups`, `teachers`, `courses`, `assignments` | dane wejściowe (komplet pięciu plików) | *Import danych* |

Opis kolumn, dozwolonych wartości i reguł walidacji: [`docs/format-importu.md`](../../docs/format-importu.md).

Przed importem usuń przykładowe wiersze. Przykład w `assignments` pokazuje zajęcia łączone:
`INF-2A|INF-2B` to jeden wykład dla dwóch grup.
