<#
.SYNOPSIS
    Uruchamia aplikację lokalnie na Windowsie bez Dockera i bez uprawnień administratora.

.DESCRIPTION
    Przy pierwszym uruchomieniu pobiera do katalogu .tools\ w projekcie:
      - uv (menedżer Pythona) i Python 3.12,
      - przenośny Node.js 22 LTS (z weryfikacją sumy SHA-256),
    a potem instaluje zależności backendu i frontendu. Kolejne uruchomienia korzystają
    z tego, co już jest pobrane (instalacja zależności tylko po ich zmianie).

    Backend działa na bazie SQLite (backend\dev.db) zamiast PostgreSQL – wystarczy do demo.
    Nic nie jest instalowane w systemie; żeby wszystko usunąć, skasuj katalog .tools\.

    Zatrzymanie: Ctrl+C w tym oknie (albo zamknięcie okna).

.EXAMPLE
    scripts\start-local.cmd
    powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1 -ResetDatabase
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    # Usuwa lokalną bazę SQLite przed startem (czysta baza).
    [switch]$ResetDatabase,
    # Nie otwiera przeglądarki po starcie.
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # pasek postępu bardzo spowalnia pobieranie w PS 5.1
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root '.tools'
$Logs = Join-Path $Tools 'logs'
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Venv = Join-Path $Backend '.venv-local'

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "BŁĄD: $Message" -ForegroundColor Red; exit 1 }

function Get-File([string]$Url, [string]$Destination) {
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
    } catch {
        Fail "Nie udało się pobrać $Url`n$($_.Exception.Message)`nSprawdź połączenie z internetem / proxy uczelni."
    }
}

function Assert-Hash([string]$File, [string]$Expected) {
    $actual = (Get-FileHash -Algorithm SHA256 -Path $File).Hash
    if ($actual -ne $Expected.Trim().ToUpper()) {
        Remove-Item $File -Force
        Fail "Suma kontrolna pliku $(Split-Path -Leaf $File) się nie zgadza – plik usunięty, uruchom skrypt ponownie."
    }
}

function Get-ContentHash([string]$File) { (Get-FileHash -Algorithm SHA256 -Path $File).Hash }

function Test-PortFree([int]$Port) {
    $listening = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    return -not ($listening | Where-Object { $_.Port -eq $Port })
}

New-Item -ItemType Directory -Force -Path $Tools, $Logs | Out-Null

# Wszystko, co pobiera uv (Python, cache), trzymamy w projekcie, a nie w profilu użytkownika.
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Tools 'python'
$env:UV_CACHE_DIR = Join-Path $Tools 'uv-cache'
$env:UV_NO_MODIFY_PATH = '1'

# --- 1. uv + Python 3.12 ---------------------------------------------------------------------
$UvDir = Join-Path $Tools 'uv'
$Uv = Join-Path $UvDir 'uv.exe'
if (-not (Test-Path $Uv)) {
    Write-Step 'Pobieranie uv (menedżer Pythona)...'
    $zip = Join-Path $Tools 'uv.zip'
    $base = 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip'
    Get-File $base $zip
    Get-File "$base.sha256" "$zip.sha256"
    Assert-Hash $zip ((Get-Content "$zip.sha256" -Raw).Split(' ')[0])
    Expand-Archive -Path $zip -DestinationPath $UvDir -Force
    Remove-Item $zip, "$zip.sha256" -Force
}

$VenvPython = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    Write-Step 'Instalowanie Pythona 3.12 i tworzenie środowiska backendu...'
    & $Uv venv $Venv --python 3.12 --quiet
    if ($LASTEXITCODE -ne 0) { Fail 'Nie udało się utworzyć środowiska Pythona.' }
}

$requirements = Join-Path $Backend 'requirements.txt'
$reqStamp = Join-Path $Venv '.requirements.sha256'
$reqHash = Get-ContentHash $requirements
if (-not (Test-Path $reqStamp) -or (Get-Content $reqStamp -Raw).Trim() -ne $reqHash) {
    Write-Step 'Instalowanie zależności backendu...'
    & $Uv pip install --python $VenvPython -r $requirements --quiet
    if ($LASTEXITCODE -ne 0) { Fail 'Instalacja zależności backendu nie powiodła się.' }
    Set-Content -Path $reqStamp -Value $reqHash
}

# --- 2. Node.js 22 LTS -----------------------------------------------------------------------
$NodeDir = Get-ChildItem -Path (Join-Path $Tools 'node') -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName 'node.exe') } | Select-Object -First 1
if (-not $NodeDir) {
    Write-Step 'Pobieranie Node.js 22 LTS (wersja przenośna)...'
    $dist = 'https://nodejs.org/dist/latest-v22.x'
    $sums = Join-Path $Tools 'SHASUMS256.txt'
    Get-File "$dist/SHASUMS256.txt" $sums
    $line = Select-String -Path $sums -Pattern 'node-v22[^ ]*-win-x64\.zip$' | Select-Object -First 1
    if (-not $line) { Fail 'Nie znaleziono paczki Node.js dla Windows x64.' }
    $expected, $name = $line.Line -split '\s+'
    $zip = Join-Path $Tools $name
    Get-File "$dist/$name" $zip
    Assert-Hash $zip $expected
    Expand-Archive -Path $zip -DestinationPath (Join-Path $Tools 'node') -Force
    Remove-Item $zip, $sums -Force
    $NodeDir = Get-ChildItem -Path (Join-Path $Tools 'node') -Directory | Select-Object -First 1
}
$Node = Join-Path $NodeDir.FullName 'node.exe'
$env:PATH = "$($NodeDir.FullName);$env:PATH"   # npm wywołuje node z PATH

$lock = Join-Path $Frontend 'package-lock.json'
$lockStamp = Join-Path $Frontend 'node_modules\.package-lock.sha256'
$lockHash = Get-ContentHash $lock
if (-not (Test-Path $lockStamp) -or (Get-Content $lockStamp -Raw).Trim() -ne $lockHash) {
    Write-Step 'Instalowanie zależności frontendu (npm ci)...'
    Push-Location $Frontend
    try {
        & (Join-Path $NodeDir.FullName 'npm.cmd') ci --no-fund --no-audit --loglevel=error
        if ($LASTEXITCODE -ne 0) { Fail 'Instalacja zależności frontendu nie powiodła się.' }
    } finally {
        Pop-Location
    }
    Set-Content -Path $lockStamp -Value $lockHash
}

# --- 3. Start ----------------------------------------------------------------------------------
foreach ($port in $BackendPort, $FrontendPort) {
    if (-not (Test-PortFree $port)) {
        Fail "Port $port jest zajęty (może aplikacja już działa?). Zamknij ten program albo użyj -BackendPort / -FrontendPort."
    }
}

$dbFile = Join-Path $Backend 'dev.db'
if ($ResetDatabase -and (Test-Path $dbFile)) {
    Write-Step 'Usuwanie lokalnej bazy danych...'
    Remove-Item $dbFile -Force
}

# Zmienne środowiskowe dziedziczą uruchamiane procesy.
$env:DATABASE_URL = 'sqlite+pysqlite:///./dev.db'   # względem katalogu backend\
$env:ENVIRONMENT = 'development'
# 127.0.0.1 zamiast localhost: Node potrafi rozwiązać localhost na IPv6 (::1), a backend słucha na IPv4.
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:$BackendPort"

Write-Step 'Uruchamianie backendu i frontendu...'
$backendProc = Start-Process -FilePath $VenvPython -WorkingDirectory $Backend -NoNewWindow -PassThru `
    -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $BackendPort `
    -RedirectStandardOutput (Join-Path $Logs 'backend.log') -RedirectStandardError (Join-Path $Logs 'backend.err.log')
$frontendProc = Start-Process -FilePath $Node -WorkingDirectory $Frontend -NoNewWindow -PassThru `
    -ArgumentList 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', $FrontendPort, '--strictPort' `
    -RedirectStandardOutput (Join-Path $Logs 'frontend.log') -RedirectStandardError (Join-Path $Logs 'frontend.err.log')

try {
    # Czekamy, aż backend odpowie (pierwszy start tworzy tabele w bazie).
    $healthUrl = "http://127.0.0.1:$BackendPort/api/health"
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        if ($backendProc.HasExited) { break }
        try {
            $ready = (Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2).status -eq 'ok'
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        Write-Host (Get-Content (Join-Path $Logs 'backend.err.log') -Tail 20 | Out-String)
        Fail "Backend nie wystartował. Logi: $Logs"
    }

    # Czekamy też na serwer Vite.
    $appUrl = "http://127.0.0.1:$FrontendPort"
    for ($i = 0; $i -lt 30 -and -not $frontendProc.HasExited; $i++) {
        try {
            Invoke-WebRequest -Uri $appUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if ($frontendProc.HasExited) {
        Write-Host (Get-Content (Join-Path $Logs 'frontend.err.log') -Tail 20 | Out-String)
        Fail "Frontend nie wystartował. Logi: $Logs"
    }

    Write-Host ''
    Write-Host '  Aplikacja działa:' -ForegroundColor Green
    Write-Host "    Frontend:       $appUrl"
    Write-Host "    API (Swagger):  http://127.0.0.1:$BackendPort/api/docs"
    Write-Host "    Baza danych:    $dbFile"
    Write-Host "    Logi:           $Logs"
    Write-Host ''
    Write-Host '  Ctrl+C zatrzymuje aplikację.' -ForegroundColor Yellow

    if (-not $NoBrowser) { Start-Process $appUrl }

    while (-not $backendProc.HasExited -and -not $frontendProc.HasExited) {
        Start-Sleep -Seconds 1
    }
    if ($backendProc.HasExited) { Write-Host "Backend się zatrzymał – logi: $Logs" -ForegroundColor Red }
    if ($frontendProc.HasExited) { Write-Host "Frontend się zatrzymał – logi: $Logs" -ForegroundColor Red }
} finally {
    # Wykonuje się także po Ctrl+C.
    foreach ($proc in $backendProc, $frontendProc) {
        if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    }
    Write-Host 'Zatrzymano aplikację.'
}
