# ASZF Q&A Agent (POC)

Belső ügyintézői copilot telekom ügyfélszolgálati munkához. A rendszer ÁSZF-forrásokból keres, válaszlevél-draftot készít, eszkalációt javasol, és auditálható human-in-the-loop folyamatot tart fenn. Nem autonóm ügyfélkommunikációs agent.

Fejlesztés közben kötelező iránytű: [docs/specs/FEJLESZTESI_GUARDRAILS.md](docs/specs/FEJLESZTESI_GUARDRAILS.md).

## Quick Start

Három parancs az induláshoz (Docker nem szükséges):

```powershell
python -m venv .venv ; .venv\Scripts\activate ; pip install -r requirements.txt
copy .env.example .env
.\start.ps1
```

A `start.ps1` automatikusan inicializálja az adatbázist, buildeli a frontendet (első indításkor), és egyetlen folyamatban kiszolgálja az API-t és a React SPA-t a `http://localhost:8000` címen. OpenAI-kulcs nélkül determinisztikus fallback módban fut.

Demo belépések: `ui_demo` / `ui_demo` vagy `supervisor_demo` / `supervisor_demo`.

> Fejlesztői módban (backend + frontend külön): lásd [docs/operations/development_guide.md](docs/operations/development_guide.md).

## Architektúra

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│  React SPA  │────▶│  FastAPI Backend (backend/)               │
│  (frontend/)│◀────│  ├─ PII maszkolás (Presidio)             │
└─────────────┘     │  ├─ Osztályozás (LLM / szabályalapú)     │
                    │  ├─ RAG keresés (Qdrant / hybrid fallback)│
                    │  ├─ Válasz-draft (LLM / sablon)           │
                    │  ├─ Groundedness ellenőrzés                │
                    │  ├─ Eszkaláció döntéstámogatás             │
                    │  └─ RBAC + audit trail                     │
                    └──────────────────┬───────────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────────┐
                    │  LangGraph Agent Pipeline (agent/)           │
                    │  Lineáris: mask → classify → retrieve →      │
                    │  policy_map → draft → verify → escalation    │
                    │  Minden lépés: LLM-út VAGY szabályalapú      │
                    │  fallback (*_mode jelzéssel)                  │
                    └─────────────────────────────────────────────┘
```

- **AI lépések**: osztályozás, draft-generálás, groundedness-ellenőrzés, eszkaláció — mindegyik LLM-alapú, konfigurálható modellel.
- **Szabályalapú lépések**: PII-maszkolás (Presidio), RAG retrieval (Qdrant + BM25 hybrid), policy-map (YAML-szabályok), forrásjelölés.
- **Fallback**: ha az LLM nem elérhető, minden lépés determinisztikus módra vált (`classify_mode: "fallback"`, `generation_mode: "template"`, stb.).

## Konfiguráció

Minden beállítás a `.env` fájlból és a `config/` YAML-okból töltődik, a `config/settings.py` osztályon keresztül:

| Beállítás | Forrás | Leírás |
|-----------|--------|--------|
| `OPENAI_MODEL` | `.env` | LLM modell neve (alapértelmezés: `gpt-4.1`) |
| `OPENAI_TEMPERATURE` | `.env` | Generálási hőmérséklet (`0.2`) |
| `CONFIDENCE_THRESHOLD` | `.env` | Osztályozási konfidencia-küszöb (`0.75`) |
| `LLM_ENABLED` | `.env` | `false` → teljes szabályalapú mód |
| `QDRANT_MODE` | `.env` | `local` (beágyazott) vagy `server` (külső) |
| Szabályzat-térkép | `config/policies.yaml` | Kategória → kötelező ÁSZF-hivatkozások |
| Megőrzési szabályok | `config/retention.yaml` | Audit-log megőrzési idők |
| Eval konfiguráció | `config/eval.yaml` | Kiértékelési futtatás paraméterei |

A promptok verziózott fájlokban élnek: `prompts/` mappa (lásd [Prompt katalógus](docs/specs/ASZF_QnA_Agent_prompt_katalogus.md)).

## Fő API-folyamat

Tipikus vertikális flow:

1. `POST /mask` — visszafordítható PII-maszkolás
2. `POST /classify` — kategória, konfidencia, prompt-injection jelzés
3. `GET /history` és `GET /customer-lookup` — előzmény és mock ügyféltörzs
4. `POST /retrieve` — forráskeresés Qdrant vagy lokális hybrid fallback alapján
5. `POST /policy-map` — szabályzat-térkép és kötelező hivatkozások
6. `POST /draft` — forrásolt válaszjavaslat
7. `POST /verify` — groundedness ellenőrzés
8. `POST /unmask` — RBAC-védett visszafejtés jóváhagyás előtt
9. `POST /agent/run` — teljes LangGraph ügyfeldolgozás

Minden API-válasz tartalmazza: `request_id`, `model_profile`, `prompt_version`, `aszf_version`.

## Frontend

A `frontend/` az aktív ügyintézői felület. Fő nézetek: Login, Inbox, Ügy-munkaállomás, Új ügy, Copilot, Postai import, Evaluation, Supervisor, Knowledge.

Kapcsolódó: [frontend/README.md](frontend/README.md) | [frontend/UX-DECISIONS.md](frontend/UX-DECISIONS.md)

## Mock réteg és éles integráció

A PoC mock-rétege (`integrations/`) elkülönített adaptereken keresztül működik, így az éles integrációra váltás az adapter cseréjét jelenti, nem a core logika módosítását:

| Mock adapter | Fájl | Éles váltás |
|---|---|---|
| Ügyfél-keresés | `integrations/customer_directory.py` | CRM API adapter |
| Ügyelet-tároló | `integrations/case_store.py` | Ticketing rendszer adapter |
| Email küldés | `integrations/email_adapter.py` | SMTP / Exchange adapter |

## Audit, governance, evaluation

- Audit endpointok: `GET /audit/cases/{id}`, `GET /audit/events`, `GET /audit/completeness/{id}`
- Státusz workflow: `POST /cases/status`
- Megőrzés: `config/retention.yaml`, `POST /governance/purge`
- Evaluation API: `POST /eval/run`, `GET /eval/runs/{run_id}`, `POST /eval/baseline`, `POST /eval/human-score`
- Acceptance kapu: `POST /acceptance/run`
- Demó: `POST /demo/run`

Kapcsolódó: [DPIA](docs/governance/dpia.md) | [Compliance checklist](docs/governance/compliance_checklist.md) | [Demó forgatókönyv](docs/operations/demo_script.md)

## Tesztelés

68 tesztfájl, hermetikus offline környezetben (nincs valódi LLM-hívás a tesztekben):

Részletek: [docs/operations/development_guide.md](docs/operations/development_guide.md).

## Projektstruktúra

| Mappa | Szerep |
|-------|--------|
| `agent/` | LangGraph állapotgép és node-ok |
| `backend/` | FastAPI API, üzleti szolgáltatások, DB, audit, governance |
| `backend/api/` | Témakör szerinti API routerek |
| `backend/services/` | Service-határok |
| `config/` | Runtime, policy, retention és eval konfiguráció |
| `prompts/` | Verziózott LLM rendszerpromptok |
| `data/` | Lokális PDF-ek, feldolgozott chunkok, mintaüzenetek, eval riportok |
| `demo/` | Automatizált demó-szcenáriók |
| `docs/` | Termék-, fejlesztési és működési dokumentáció |
| `eval/` | Evaluation harness |
| `frontend/` | Aktív React + TypeScript + Tailwind SPA |
| `integrations/` | Mock külső adapterek (CRM, ticketing, email) |
| `preprocessing/` | Ingest, parse, embedding, indexelés, smoke CLI-k |
| `scripts/` | Quality gate és diagnosztikai segédprogramok |
| `security/` | RBAC, prompt guard, redakció |
| `tests/` | 68 pytest regressziós és kontraktusteszt-fájl |

## Ismert korlátok és PoC → production út

| Terület | PoC állapot | Production cél |
|---------|-------------|----------------|
| Adatbázis | SQLite | PostgreSQL |
| Vektortár | Beágyazott Qdrant | Qdrant szerver klaszter |
| Auth | Demo login (hardcoded) | SSO / LDAP integráció |
| Observability | Fájl-alapú trace | Langfuse / OpenTelemetry |
| Üzenet-feldolgozás | Szinkron API | Celery / üzenetsor |
| PII-maszkolás | Presidio lokális | Presidio + custom NER |
| Logok | PII-mentes (maszkolás után logolunk) | Centralizált log-aggregátor |

Részletes roadmapek: [docs/roadmaps/](docs/roadmaps/).

## Dokumentáció

Belépési pont: [docs/README.md](docs/README.md).

- `docs/specs/` — üzleti, technikai, frontend, contract, prompt specifikációk és guardrailek
- `docs/roadmaps/` — UI, RAG, agentic és kódbázis roadmapek
- `docs/governance/` — DPIA és compliance
- `docs/operations/` — demó, fejlesztői útmutató, quality/bugfix tervek
