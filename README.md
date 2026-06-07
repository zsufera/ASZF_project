# ASZF Q&A Agent (POC)

POC-level belső copilot telekom ügyfélszolgálathoz:
- ÁSZF-alapú forráshivatkozás
- válaszlevél-javaslat
- eszkalációs döntéstámogatás
- auditálható, human-in-the-loop működés

Fejlesztés közben kötelező iránytű: [FEJLESZTESI_GUARDRAILS.md](FEJLESZTESI_GUARDRAILS.md).

## Gyors indulás

1. Python környezet és csomagok:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. Környezeti változók:
   - másold: `.env.example` -> `.env`
3. Infrastruktúra (opcionális — Docker nélkül is indulhat a POC):
   - **Docker nélkül (ajánlott első próbához):** ezt a lépést hagyd ki. A retrieval lokális fallbacket használ (`data/processed/chunks.jsonl`), Qdrant nem kell.
   - **Dockerrel (opcionális Qdrant / Ollama / Langfuse):**
     - telepítsd a [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) alkalmazást, indítsd el, majd:
     - `docker compose up -d`
     - ha a `docker` parancs nem ismert: Docker Desktop nincs telepítve vagy nincs a PATH-ban — használd a Docker nélküli útvonalat fent.
4. Adatbázis inicializálás:
   - `python -m backend.db`
5. Backend indítás:
   - `uvicorn backend.main:app --reload`
6. Streamlit UI (Fázis 4):
   - `streamlit run ui/app.py`
   - demo belépés: `ui_demo` / `ui_demo` vagy `supervisor_demo` / `supervisor_demo`

## ÁSZF ingest első lépései

Másold a PDF-eket a `data/raw_pdfs/` mappába (POC elsődleges út).

1. Manifest generálás:
   - `python -m preprocessing.manifest`
   - kimenet: `data/ingest_manifest.json`
2. PDF parse + hierarchikus chunkolás:
   - `python -m preprocessing.parse`
   - kimenetek:
     - `data/processed/parsed_pages.jsonl`
     - `data/processed/chunks.jsonl`
3. Indexelés:
   - `python -m preprocessing.index --skip-qdrant` (lokális sparse fallback)
   - `python -m preprocessing.index` (Qdrant, ha fut a compose)
4. Dok-paraméterezés (Fázis 1b):
   - `python -m preprocessing.derive_params`
   - kimenetek: `config/policies.yaml`, `config/mandatory_refs.yaml`, `config/disclaimer.yaml`, `data/derived/derive_report.json`
5. Minta-emailek:
   - `python -m preprocessing.gen_emails`
   - kimenet: `data/sample_emails/`
6. Smoke ellenőrzés:
   - `python -m preprocessing.smoke_retrieve "számlázási kifogás" --service-provider ONE`
   - `python -m preprocessing.smoke_ingest --query "számlázási kifogás" --service-provider ONE`

Opcionális letöltő: `python -m preprocessing.download` (WAF esetén nem megbízható).

Ha nincs PDF a `data/raw_pdfs/` alatt, a manifest üres dokumentumlistával jön létre.
A `/retrieve` endpoint a `data/processed/chunks.jsonl` alapján lokális fallback keresést ad, így Qdrant nélkül is tesztelhető a forráshivatkozásos találat.

## Backend flow (Fázis 2)

Indítás: `uvicorn backend.main:app --reload`

Vertikális sorrend:

1. `POST /mask` -> visszafordítható PII-maszkolás (SQLite token-térkép)
2. `POST /classify` -> kategória + konfidencia + ismétlődés-jelzés
3. `GET /history?address=` -> azonos feladó előzményei (SQLite)
4. `GET /customer-lookup?address=` -> mock ügyféltörzs-jelöltek
5. `POST /retrieve` -> hibrid (sparse+dense) retrieval, cross-ref bővítés, opcionális Qdrant
6. `POST /policy-map` -> szabályzat-térkép + kötelező hivatkozások
7. `backend.escalation.decide_escalation()` -> eszkalációs helper
8. `POST /draft` -> válaszjavaslat citationökkel
9. `POST /verify` -> groundedness ellenőrzés
10. `POST /unmask` -> draft visszafejtés jóváhagyás előtt
11. `POST /ocr` -> postai PDF szövegkinyerés + maszkolás
12. `POST /reindex` -> manifest + parse + index + derive_params
13. `POST /eval/run` -> minta-email alapú retrieval/osztályozás metrikák
14. `POST /agent/run` -> LangGraph állapotgép végponttól független teljes agent-folyamat

Minden válasz tartalmazza: `request_id`, `model_profile`, `prompt_version`, `aszf_version`.

## Agent flow (Fázis 3)

`POST /agent/run` mezők: `case_id`, `channel` (`email|chat|phone|postal`), `input_text` vagy `input_text_masked`, opcionálisan `sender_email`, `service_provider`, `output_mode`.

Lépések: nyelv/típus → maszkolás → kontextus → osztályozás → prioritás → retrieval → policy-map → eszkaláció → intézkedés → draft → verify → unmask-előkészítés.

Válasz tartalmazza a `timeline` listát UI-idővonalhoz.

## Streamlit UI (Fázis 4)

Indítás: `streamlit run ui/app.py` (a backend fusson: `uvicorn backend.main:app --reload`).

Nézetek:
- **Inbox** — minta-emailek listája, szűrés/rendezés, ügy nézet
- **Szabad bevitel** — ad-hoc feldolgozás
- **Csatornák** — email / chat / telefon copilot / postai PDF+OCR
- **Evaluation** — `/eval/run` KPI-k
- **Supervisor** — eszkalált sor + aggregált statisztika

Ügy nézet: háromhasábos elrendezés (források, draft-szerkesztő, agent-idővonal), jóváhagyás mock küldéssel, ÜI-visszajelzés.

Backend ügy-endpointok: `GET /inbox`, `GET /cases/{id}`, `POST /cases/process`, `POST /cases/draft`, `POST /cases/approve`, `POST /cases/feedback`, `GET /supervisor/*`.

## Audit és governance (Fázis 5)

- Strukturált audit: `GET /audit/cases/{id}`, `GET /audit/events`, `GET /audit/completeness/{id}`
- Státusz workflow: `POST /cases/status`
- RBAC: `/unmask` és jóváhagyás `role` + `username` mellett; minden PII-hozzáférés naplózva
- Megőrzés: `config/retention.yaml`, `POST /governance/purge` (supervisor, dry-run alap)
- DPIA: [docs/dpia.md](docs/dpia.md)

## Evaluation harness (Fázis 6)

CLI: `python -m eval.run_eval --limit 10`

API:
- `POST /eval/run` — teljes KPI riport (szűrők: kategória, szolgáltató, edge esetek)
- `GET /eval/runs/{run_id}` — mentett futás
- `POST /eval/baseline` + `GET /eval/baseline` — regresszió diff
- `POST /eval/human-score` — emberi 1–5 spot-check

KPI célértékek: `config/eval_targets.yaml`. Riportok: `data/eval/runs/`.

## POC lezárás (Fázis 7)

Demó-szcenáriók:
- `python -m demo` vagy `POST /demo/run`
- Forgatókönyv: [docs/demo_script.md](docs/demo_script.md)

Elfogadási kapu:
- `python scripts/run_quality_gate.py` (pytest + eval KPI + demó)
- `POST /acceptance/run`

Observability:
- `GET /observability/traces` — lokális trace (`data/traces/`)
- Opcionális Langfuse: `docker compose --profile observability up -d`, `.env`: `LANGFUSE_ENABLED=true`

Integrációs adapterek (mock):
- `integrations/sqlite_case_store.py` — `CaseStore` Protocol
- `integrations/mock_email_adapter.py` — outbound mock küldés

Compliance: [docs/compliance_checklist.md](docs/compliance_checklist.md)

## Projektváz

- `preprocessing/` letöltés, parse, chunk, index, mintaadat
- `backend/` FastAPI API + DB
- `agent/` LangGraph állapotgép
- `ui/` Streamlit felület
- `eval/` referencia-mentes kiértékelés
- `demo/` automatizált demó-szcenáriók
- `integrations/` külső rendszer adapterek (mock)
- `scripts/` minőség-kapu és segéd CLI-k
- `config/` policy és runtime konfig
- `data/` lokális adatok
- `docs/` DPIA, demó forgatókönyv, compliance
