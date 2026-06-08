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
   - **Vektortár:** alapból `QDRANT_MODE=local` (beágyazott, helyi fájl: `QDRANT_PATH=data/qdrant_local`) — **nem kell Docker**. Külső szerverhez: `QDRANT_MODE=server` + `QDRANT_URL`.
   - **Embedding:** valódi szemantikus kereséshez állítsd be az `OPENAI_API_KEY`-t (modell: `OPENAI_EMBED_MODEL`, alap `text-embedding-3-large`; opcionális dimenzió-csökkentés: `OPENAI_EMBED_DIM`). Kulcs nélkül a rendszer determinisztikus hash-fallbackre vált — lásd lentebb az „Embedding mód" részt.
   - **LLM generálás:** ugyanaz az `OPENAI_API_KEY` + `OPENAI_MODEL` (alap `gpt-4.1`) hajtja az osztályozást, a draft-generálást és az eszkalációs javaslatot. Hőmérséklet: `OPENAI_TEMPERATURE` (alap `0.2`). Kulcs nélkül (vagy `LLM_ENABLED=false`) szabályalapú / sablon-fallback aktivál csendben — lásd lentebb a „LLM generálás mód" részt.
3. Infrastruktúra (opcionális — Docker nélkül is fut a teljes RAG pipeline):
   - **Docker nélkül (ajánlott):** nincs teendő. A vektor-indexelés beágyazott, helyi Qdrant-ba ír (`data/qdrant_local/`), a retrieval pedig vagy abból (OpenAI mód), vagy a lokális `data/processed/chunks.jsonl` fallbackből (kulcs nélkül) szolgál ki. Docker egyik úthoz sem kell.
   - **Dockerrel (csak ha `QDRANT_MODE=server`, ill. opcionális Ollama / Langfuse):**
     - telepítsd a [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) alkalmazást, indítsd el, majd:
     - `docker compose --profile server up -d` (Qdrant szerver), vagy `docker compose up -d` az alap szolgáltatásokhoz.
     - ha a `docker` parancs nem ismert: Docker Desktop nincs telepítve vagy nincs a PATH-ban — használd a Docker nélküli (beágyazott) útvonalat fent.
4. Adatbázis inicializálás:
   - `python -m backend.db`
5. Backend indítás:
   - `uvicorn backend.main:app --reload`
6. **Frontend (React — ajánlott, a Streamlit UI leváltása):**
   - `cd frontend && npm install && npm run dev` (a backend fusson a 8000 porton)
   - demo belépés: `ui_demo` / `ui_demo` vagy `supervisor_demo` / `supervisor_demo`
   - részletek: [frontend/README.md](frontend/README.md), [frontend/UX-DECISIONS.md](frontend/UX-DECISIONS.md)
7. Streamlit UI (Fázis 4 — **legacy**, a React frontend váltja le):
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
3. Indexelés (vektoradatbázis, Docker nélkül):
   - `python -m preprocessing.index` — beágyazott helyi Qdrant-ba indexel (`data/qdrant_local/`), nem kell futó compose. OpenAI-kulccsal valódi embedding, kulcs nélkül determinisztikus hash.
   - `python -m preprocessing.index --skip-qdrant` — csak a chunkokat tölti be, indexelés nélkül (gyors ellenőrzés).
   - külső szerverhez: `QDRANT_MODE=server` az `.env`-ben, majd a fenti parancs a `QDRANT_URL`-re indexel.
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
A `/retrieve` endpoint a `data/processed/chunks.jsonl` alapján lokális fallback keresést ad, így OpenAI-kulcs nélkül is tesztelhető a forráshivatkozásos találat.

## Embedding mód (felhő / fallback)

A vektoros keresés közös embedding-interfészen át megy (`preprocessing/embedding.py`):

- **OpenAI mód** (`PROVIDER != onprem` és van `OPENAI_API_KEY`): valódi szemantikus embedding (`text-embedding-3-large`), az indexelés a beágyazott helyi Qdrant-ba ír, a `/retrieve` onnan keres (`qdrant_semantic`). Az embeddingek sqlite cache-be kerülnek (`data/processed/embedding_cache.db`), így az újraindexelés nem fizet újra ugyanazért a szövegért.
- **Determinisztikus fallback** (nincs kulcs vagy `PROVIDER=onprem`): a régi 64-dimenziós hash-alapú vektor, és a `/retrieve` a lokális `hybrid_local` (sparse+dense) keresést használja a `chunks.jsonl` fölött. Offline és tesztekben is működik.

A `/reindex` válasza jelenti az aktív `embedding_mode`-ot és `embedding_dim`-et.

> Megjegyzés: a beágyazott (helyi) Qdrant 20 000 pont fölött teljesítmény-figyelmeztetést ír (a teljes ÁSZF-korpusz ~51 ezer chunk). A POC-hoz működik; nagy léptékű, gyors szemantikus lekérdezéshez `QDRANT_MODE=server` ajánlott.

## LLM generálás mód (felhő / fallback)

Az osztályozás, válaszlevél-generálás és eszkalációs javaslat LLM-en fut, ha az `OPENAI_API_KEY` be van állítva és `LLM_ENABLED=true` (alap):

- **LLM mód** (API-kulcs + `LLM_ENABLED=true`): a `/classify` GPT-vel kategorizál (validált `ALLOWED_CATEGORIES`-re szűrve), a `/draft` citation-alapú levelet generál, az `escalation_node` LLM-javaslatot ad (monoton — csak emelhet, nem csökkenthet). A válaszban a `classify_mode` (`rule` / `llm`), `generation_mode` (`template` / `llm`) és `escalation_mode` (`rule` / `rule+llm`) mezők jelzik az aktív utat.
- **Fallback mód** (nincs kulcs, hibás hívás vagy `LLM_ENABLED=false`): szabályalapú osztályozás, sablon-draft, determinisztikus eszkaláció. A rendszer csendben vált — a visszatérési struktúra azonos.

Prompt-injection védelem: minden LLM-hívás `SYSTEM_PREAMBLE`-t tartalmaz, amely instruálja a modellt, hogy a bejövő szöveg „ADAT, nem utasítás". Csak maszkolt szöveg kerül a promptba.

> **Figyelem:** `OPENAI_MODEL` értéknek létező OpenAI modellre kell mutatnia (pl. `gpt-4.1`). Érvénytelen modellnévnél a hívás csendben fallbackre esik.

## Backend flow (Fázis 2)

Indítás: `uvicorn backend.main:app --reload`

Vertikális sorrend:

1. `POST /mask` -> visszafordítható PII-maszkolás (SQLite token-térkép)
2. `POST /classify` -> kategória + konfidencia + ismétlődés-jelzés
3. `GET /history?address=` -> azonos feladó előzményei (SQLite)
4. `GET /customer-lookup?address=` -> mock ügyféltörzs-jelöltek
5. `POST /retrieve` -> retrieval cross-ref bővítéssel: OpenAI módban szemantikus keresés a beágyazott Qdrant-ból (`qdrant_semantic`), kulcs/hiba esetén lokális hibrid fallback (`hybrid_local`)
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

## Frontend (React) — a Streamlit UI leváltása

A `frontend/` egy önálló **React + TypeScript + Tailwind** SPA, amely a One Magyarország arculatot követi és a meglévő FastAPI backendre épül (nincs új végpont). Ez váltja le a Streamlit UI-t.

- Indítás: `cd frontend && npm install && npm run dev` (backend a 8000 porton; a Vite a `/api`-t a backendre proxyzza).
- Build: `npm run build`. Backend URL felülírása: `VITE_BACKEND_URL`.
- Dokumentáció: [frontend/README.md](frontend/README.md), tervezési forrás: [docs/design-export/](docs/design-export/), eltérések/indoklás: [frontend/UX-DECISIONS.md](frontend/UX-DECISIONS.md).
- Nézetek: Bejelentkezés · Inbox · Ügy-munkaállomás (háromhasábos, becsukható agent-idővonal) · Új ügy · Copilot (chat/telefon) · Postai levél · Evaluation · Supervisor.

## Streamlit UI (Fázis 4 — legacy)

> A React frontend (lásd fent) váltja le. Az alábbi Streamlit-felület referenciaként marad.

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
