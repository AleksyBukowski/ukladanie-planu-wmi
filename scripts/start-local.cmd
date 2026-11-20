@echo off
rem Uruchamia aplikacje lokalnie bez Dockera i bez admina - szczegoly w start-local.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1" %*
if errorlevel 1 pause
