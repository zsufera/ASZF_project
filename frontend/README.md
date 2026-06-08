# ÁSZF Copilot — React Frontend

React SPA replacing the Streamlit `ui/` for the ÁSZF Q&A Copilot (One Magyarország).

## Requirements

- Node 18+ (tested with Node 24 / npm 11)
- Backend running at `http://127.0.0.1:8000` (FastAPI)

## Development

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173`. API calls to `/api/*` are proxied to `http://127.0.0.1:8000`.

## Production build

```bash
npm run build
```

Output goes to `frontend/dist/`. Serve with any static file server; configure it to rewrite all paths to `index.html` for client-side routing.

## Environment variable

| Variable | Default | Description |
|---|---|---|
| `VITE_BACKEND_URL` | `/api` | Base URL for all API calls. In dev, `/api` is proxied to `:8000`. In production, set to the full backend URL if not behind the same origin. |

Example `.env.local`:
```
VITE_BACKEND_URL=http://127.0.0.1:8000
```

## Relation to Streamlit UI

This SPA replaces `ui/` (Streamlit). The FastAPI backend is unchanged — all endpoints are the same. To run only the new frontend:

1. Start the backend: `uvicorn backend.main:app --reload`
2. Start the frontend dev server: `cd frontend && npm run dev`
3. Open `http://localhost:5173`

## Demo credentials

- `ui_demo` / `ui_demo` — standard agent role
- `supervisor_demo` / `supervisor_demo` — supervisor role (unlocks `/supervisor`)
