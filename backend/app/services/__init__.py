"""Logika biznesowa niezależna od HTTP: parsery importu, walidacja kolizji, eksport.

Endpointy w `app/api/routes` powinny być cienkie i wołać funkcje z tego pakietu –
dzięki temu łatwo je testować w pytest bez uruchamiania serwera.
"""
