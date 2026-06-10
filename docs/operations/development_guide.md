# Fejlesztői útmutató

## Backend + frontend külön futtatás (fejlesztési mód)

```powershell
# Backend (auto-reload)
uvicorn backend.main:app --reload

# Frontend (külön terminál)
cd frontend
npm install
npm run dev
```

A Vite dev szerver `http://localhost:5173` címen indul, és a `/api` hívásokat a `http://127.0.0.1:8000` backendre proxyzza.

## ÁSZF ingest pipeline

Elsődleges bemenet: PDF-ek a `data/raw_pdfs/` mappában.

```powershell
python -m preprocessing.manifest
python -m preprocessing.parse
python -m preprocessing.index
python -m preprocessing.derive_params
python -m preprocessing.gen_emails
```

Kimenetek:

- `data/ingest_manifest.json`
- `data/processed/parsed_pages.jsonl`
- `data/processed/chunks.jsonl`
- `config/policies.yaml`
- `config/mandatory_refs.yaml`
- `config/disclaimer.yaml`
- `data/sample_emails/`

## Smoke ellenőrzés

```powershell
python -m preprocessing.smoke_retrieve "számlázási kifogás" --service-provider ONE
python -m preprocessing.smoke_ingest --query "számlázási kifogás" --service-provider ONE
```

## Tesztelés

Backend (hermetikus offline környezet, nincs valódi LLM-hívás):

```powershell
python -m pytest tests/ -q
```

Frontend típusellenőrzés és build:

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Quality gate (teljes ellenőrzés):

```powershell
python scripts/run_quality_gate.py
```

A `tests/conftest.py` hermetikusan offline OpenAI-környezetet állít be. LLM-viselkedést igénylő tesztek explicit monkeypatch-csel opt-inelnek.

## Demó futtatás

```powershell
python -m demo
```

Vagy API-n: `POST /demo/run`

Forgatókönyv: [demo_script.md](demo_script.md)
