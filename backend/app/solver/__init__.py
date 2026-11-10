"""Moduł generowania planu (P-03, Google OR-Tools CP-SAT).

Solver powinien przyjmować zwykłe struktury danych (dataclassy), a nie obiekty ORM,
żeby dało się go uruchamiać w osobnym procesie z limitem czasu (FR-11) i testować
na małych, ręcznie zbudowanych przykładach.
"""
