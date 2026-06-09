# ASZF QnA copilot - egykattintasos inditas (Docker nelkul).
# Buildeli a frontendet (csak az elso inditaskor), majd a backend EGY folyamatban
# kiszolgalja az API-t ES a feluletet: http://localhost:8000
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Nincs .venv. Eloszor: python -m venv .venv ; .venv\Scripts\activate ; pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "Frontend build (elso inditas, eltarthat egy percig)..."
    Push-Location frontend
    npm install
    if ($?) { npm run build }
    Pop-Location
}

Write-Host "Az alkalmazas indul: http://localhost:8000"
Write-Host "(Ujraepiteshez torold a frontend\dist mappat, vagy: cd frontend; npm run build)"
Start-Job { Start-Sleep 4; Start-Process "http://localhost:8000" } | Out-Null
& ".venv\Scripts\python.exe" -m uvicorn backend.serve:app --host 127.0.0.1 --port 8000
