"""Production ASGI app: egyetlen folyamat szolgálja ki az API-t ÉS a buildelt React SPA-t.

Futtatás: `uvicorn backend.serve:app --host 127.0.0.1 --port 8000` (a `start.bat` ezt teszi).
- `/api/*` -> a meglévő FastAPI API (a frontend alapból `/api`-t hív).
- minden más -> a `frontend/dist` statikus fájljai, SPA-fallbackkel az index.html-re
  (a react-router kliens-oldali útvonalaihoz).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.main import app as api_app
from backend.main import on_startup as _api_startup

DIST = Path("frontend/dist")

app = FastAPI(title="ASZF QnA — production (API + SPA)")


@app.on_event("startup")
def _startup() -> None:
    # A mountolt sub-app saját startupja nem fut le automatikusan → itt hívjuk az initet.
    _api_startup()


app.mount("/api", api_app)


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> FileResponse:
    """Statikus fájl, ha létezik; egyébként index.html (SPA kliens-oldali útvonalak)."""
    candidate = (DIST / full_path).resolve()
    if candidate.is_file() and DIST.resolve() in candidate.parents:
        return FileResponse(candidate)
    index = DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(
        status_code=404,
        detail="A frontend nincs buildelve. Futtasd: cd frontend && npm run build",
    )
