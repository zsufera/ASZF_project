@echo off
REM ============================================================
REM  ASZF QnA copilot - egykattintasos inditas (Docker nelkul).
REM  Buildeli a frontendet (csak az elso inditaskor), majd a
REM  backend EGY folyamatban kiszolgalja az API-t ES a feluletet:
REM      http://localhost:8000
REM  Bezaras: ebben az ablakban Ctrl+C, vagy az ablak bezarasa.
REM ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HIBA] Nincs .venv. Eloszor hozd letre:
  echo     python -m venv .venv
  echo     .venv\Scripts\activate
  echo     pip install -r requirements.txt
  pause
  exit /b 1
)

if not exist "frontend\dist\index.html" (
  echo Frontend build (elso inditas, eltarthat egy percig)...
  pushd frontend
  call npm install
  call npm run build
  popd
)

echo.
echo Az alkalmazas indul: http://localhost:8000
echo (Ujraepiteshez torold a frontend\dist mappat, vagy futtasd: cd frontend ^&^& npm run build)
echo.
start "" powershell -NoProfile -Command "Start-Sleep 4; Start-Process 'http://localhost:8000'"
".venv\Scripts\python.exe" -m uvicorn backend.serve:app --host 127.0.0.1 --port 8000
