# ASZF Q&A Agent (POC)

Belső ügyintézői copilot telekom ügyfélszolgálati munkához. A rendszer ÁSZF-forrásokból keres, válaszlevél-draftot készít, eszkalációt javasol, és auditálható human-in-the-loop folyamatot tart fenn. Nem autonóm ügyfélkommunikációs agent.

Fejlesztés közben kötelező iránytű: [docs/specs/FEJLESZTESI_GUARDRAILS.md](docs/specs/FEJLESZTESI_GUARDRAILS.md).

## Aktív rendszer

- **Backend:** FastAPI API a `backend/` mappában, SQLite perzisztenciával, RBAC/audit/governance endpointokkal.
- **Agent:** LangGraph-alapú, lineáris ügyfeldolgozási pipeline az `agent/` mappában.
- **Frontend:** React + TypeScript + Tailwind SPA a `frontend/` mappában; ez az aktív UI.
- **RAG/ingest:** PDF manifest, parse, chunkolás, embedding és indexelés a `preprocessing/` mappában.
- **Evaluation/demo:** referencia-mentes eval harness az `eval/`, automatizált demók a `demo/` alatt.
- **Legacy UI:** a régi Streamlit felület `legacy/ui/` alatt maradt referenciának.

## Gyors indulás

1. Python környezet:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Környezeti változók:

   ```powershell
   copy .env.example .env
   ```

   Alapértelmezésben nincs szükség Dockerre. A `QDRANT_MODE=local` beágyazott, helyi Qdrant-indexet használ (`data/qdrant_local/`). OpenAI-kulcs nélkül a rendszer determinisztikus embedding, osztályozási és draft fallbackekkel fut.

3. Adatbázis inicializálás:

   ```powershell
   python -m backend.db
   ```

4. Backend fejlesztői futtatás:

   ```powershell
   uvicorn backend.main:app --reload
   ```

5. Frontend fejlesztői futtatás:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   A Vite dev szerver `http://localhost:5173` címen indul, és a `/api` hívásokat a `http://127.0.0.1:8000` backendre proxyzza.

6. Egykattintásos lokális futtatás:

   A repo gyökerében indítsd a `start.bat` vagy `start.ps1` fájlt. Ez buildeli a React frontendet, majd egyetlen `uvicorn backend.serve:app` folyamattal szolgálja ki az API-t és az SPA-t a `http://localhost:8000` címen.

Demo belépések:

- `ui_demo` / `ui_demo`
- `supervisor_demo` / `supervisor_demo`

## ÁSZF ingest

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

Smoke ellenőrzés:

```powershell
python -m preprocessing.smoke_retrieve "számlázási kifogás" --service-provider ONE
python -m preprocessing.smoke_ingest --query "számlázási kifogás" --service-provider ONE
```

## Fő API-folyamat

Fejlesztői indítás: `uvicorn backend.main:app --reload`

Tipikus vertikális flow:

1. `POST /mask` - visszafordítható PII-maszkolás
2. `POST /classify` - kategória, konfidencia, prompt-injection jelzés
3. `GET /history` és `GET /customer-lookup` - előzmény és mock ügyféltörzs
4. `POST /retrieve` - forráskeresés Qdrant vagy lokális hybrid fallback alapján
5. `POST /policy-map` - szabályzat-térkép és kötelező hivatkozások
6. `POST /draft` - forrásolt válaszjavaslat
7. `POST /verify` - groundedness ellenőrzés
8. `POST /unmask` - RBAC-védett visszafejtés jóváhagyás előtt
9. `POST /agent/run` - teljes LangGraph ügyfeldolgozás

Minden API-válasz tartalmazza a közös metaadatokat: `request_id`, `model_profile`, `prompt_version`, `aszf_version`.

## Frontend

A `frontend/` az aktív ügyintézői felület. Fő nézetek:

- Login
- Inbox
- Ügy-munkaállomás
- Új ügy
- Copilot
- Postai import
- Evaluation
- Supervisor
- Knowledge

Kapcsolódó dokumentumok:

- [frontend/README.md](frontend/README.md)
- [frontend/UX-DECISIONS.md](frontend/UX-DECISIONS.md)
- [docs/archive/design-export/](docs/archive/design-export/)

## Audit, governance, evaluation

- Audit endpointok: `GET /audit/cases/{id}`, `GET /audit/events`, `GET /audit/completeness/{id}`
- Státusz workflow: `POST /cases/status`
- Megőrzés: `config/retention.yaml`, `POST /governance/purge`
- Evaluation API: `POST /eval/run`, `GET /eval/runs/{run_id}`, `POST /eval/baseline`, `POST /eval/human-score`
- Acceptance kapu: `python scripts/run_quality_gate.py` vagy `POST /acceptance/run`
- Demó: `python -m demo` vagy `POST /demo/run`

Kapcsolódó docs:

- [docs/governance/dpia.md](docs/governance/dpia.md)
- [docs/governance/compliance_checklist.md](docs/governance/compliance_checklist.md)
- [docs/operations/demo_script.md](docs/operations/demo_script.md)

## Tesztelés

Backend:

```powershell
python -m pytest tests/ -q
```

Frontend:

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

A `tests/conftest.py` hermetikusan offline OpenAI-környezetet állít be. LLM-viselkedést igénylő tesztek explicit monkeypatch-csel opt-inelnek.

## Projektstruktúra

- `agent/` - LangGraph állapotgép és node-ok
- `backend/` - FastAPI API, üzleti szolgáltatások, DB, audit, governance
- `backend/api/` - témakör szerinti routerek
- `backend/services/` - újabb service-határok
- `config/` - runtime, policy, retention és eval konfiguráció
- `data/` - lokális PDF-ek, feldolgozott chunkok, mintaüzenetek, eval/demo riportok
- `demo/` - automatizált demó-szcenáriók
- `docs/` - rendezett termék-, fejlesztési és működési dokumentáció
- `eval/` - evaluation harness
- `frontend/` - aktív React SPA
- `integrations/` - mock külső adapterek
- `legacy/ui/` - archivált Streamlit UI
- `preprocessing/` - ingest, parse, embedding, indexelés, smoke CLI-k
- `scripts/` - quality gate és diagnosztikai segédprogramok
- `security/` - RBAC, prompt guard, redakció
- `tests/` - pytest regressziós és kontraktusteszt-készlet

## Dokumentáció

A docs belépési pontja: [docs/README.md](docs/README.md).

Fő csoportok:

- `docs/specs/` - üzleti, technikai, frontend, contract, prompt és fejlesztési specifikációk
- `docs/roadmaps/` - UI, RAG, agentic és kódbázis egyszerűsítési roadmapek
- `docs/governance/` - DPIA és compliance
- `docs/operations/` - demó, quality/bugfix operatív anyagok
- `docs/superpowers/` - implementációs tervek és design specek
- `docs/archive/` - történeti vagy leváltott dokumentáció
