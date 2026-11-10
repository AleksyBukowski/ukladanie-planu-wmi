# Zamockowany eksport z USOS

Pliki w tym katalogu udają eksport danych z USOS i są serwowane przez serwis `mock-usos`
(`http://localhost:8001/exports`). **Tylko dane syntetyczne** – prawdziwe dane osobowe
nigdy nie trafiają do repozytorium (NFR-04). Prawdziwe/zanonimizowane pliki trzymaj
lokalnie w `data/private/` (katalog jest w `.gitignore`).

Obecne pliki to **minimalne przykłady tymczasowe**. Docelowy format kolumn i reguły walidacji
opisuje specyfikacja importu (D-03), a pełny zbiór generuje skrypt danych syntetycznych (D-10) –
po ich przygotowaniu pliki zostaną tu podmienione.
