# Konfiguracja środowiska projektu (uruchom w katalogu projektu)
$ErrorActionPreference = "Stop"

Write-Host "==> Sprawdzam Pythona..." -ForegroundColor Cyan
python --version

if (-not (Test-Path ".venv")) {
    Write-Host "==> Tworzę środowisko wirtualne .venv..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "==> Instaluję zależności..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".git")) {
    Write-Host "==> Inicjalizuję repozytorium git..." -ForegroundColor Cyan
    git init
}

Write-Host ""
Write-Host "Gotowe. Aktywuj środowisko:  .venv\Scripts\activate" -ForegroundColor Green
Write-Host "Potem sprawdź instalację:    python check_env.py" -ForegroundColor Green
