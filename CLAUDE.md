# CLAUDE.md — operatív kontextus Claude-nak

> Ez a fájl Claude (Claude Code) számára adja a **technikai/operatív** kontextust.
> A **termék- és architektúra-elveket** a [`FEJLESZTESI_GUARDRAILS.md`](FEJLESZTESI_GUARDRAILS.md) tartalmazza — az a kötelező iránytű, **azt itt nem ismételjük**. Konfliktus esetén a guardrails és a felhasználó kérése felülír.

## Mi ez
Belső **ügyintézői copilot** telekom ügyfélszolgálatra: ÁSZF-forrásolt válasz-draft + eszkalációs döntéstámogatás. Human-in-the-loop, auditálható. **Nem** ügyféllel közvetlenül kommunikáló autonóm agent.

## Repo-térkép
- `backend/` — FastAPI API (`main.py`) + üzleti logika: `llm.py`, `draft.py` (`synthesize_answer`, `build_draft`), `classify.py`, `escalation.py`, `verify.py`, `policy_map.py`, `retrieval.py`, `masking.py`, `case_service.py`, `metadata.py`, `audit_service.py`, `eval_service.py`.
- `agent/` — LangGraph állapotgép: `graph.py` (**lineáris** pipeline), `nodes.py`, `state.py`, `runner.py`.
- `preprocessing/` — ingest: `manifest`, `parse`, `index.py`, `embedding.py`, `derive_params`, `gen_emails`, `smoke_*`.
- `frontend/` — **React + TS + Tailwind + Vite** SPA (ez az aktív UI). `src/screens`, `src/components`, `src/lib/{api,types,agentSteps}`, `src/state`.
- `ui/` — **Streamlit (legacy)**, referencia; a React váltja le.
- `eval/` — referencia-mentes kiértékelés. `config/` — `settings.py`, `policies.yaml`, `mandatory_refs.yaml`, `disclaimer.yaml`. `tests/` — pytest (`conftest.py` hermetikus). `docs/design-export/` — One design tokenek.

## Futtatás (Windows)
```powershell
# Backend (8000) — friss indítás tölti be a legutóbbi kódot
uvicorn backend.main:app --reload
# Frontend (5173)
cd frontend; npm install; npm run dev      # belépés: ui_demo / ui_demo
# Backend tesztek
.venv/Scripts/python.exe -m pytest tests/ -q
# Frontend ellenőrzés
cd frontend; npx tsc --noEmit; npm run build
```
- **PowerShell:** nincs `&&` lánc — `;` vagy külön sor. Pytest: `python -m pytest` (ne csak `pytest`).
- **`uvicorn --reload` Windows-on nem megbízhatóan tölti újra a `.py` változásokat** → backend-kód módosítása után **indítsd újra** a szervert. (A Vite frontend HMR rendben.)

## LLM-hívások — kötelező idióma (itt bukott már el a rendszer)
- Minden LLM-hívás a `backend/llm.py::chat_json(system, user)`-en megy, **JSON-object módban**.
- `llm_available()` kapu; ha nincs LLM → **determinisztikus/sablon fallback**, és állíts be egy `*_mode` mezőt (`classify_mode`, `generation_mode`, `verify_mode`, `escalation_mode`).
- A hívást `try/except`-be tedd, de **ne nyeld el némán**: `logger.exception(...)` + fallback. (A néma fallback miatt volt megkülönböztethetetlen egy konfighiba egy valódi „nincs fedezet"-től.)
- **`gpt-5` / `o1`/`o3`/`o4` modellek csak a default `temperature`-t fogadják el** → a `_chat_completion` a `_supports_custom_temperature()` alapján elhagyja a temperature-t. **Ne** vezess vissza feltétlen `temperature=`-t.
- **Csak maszkolt szöveg** mehet promptba; a `SYSTEM_PREAMBLE` a bemenetet ADAT-ként kezeli (prompt-injection védelem).

## Agent
- `agent/graph.py` **lineáris** (nincs feltételes él/ciklus). A node-ok `agent/nodes.py`-ban részleges state-et adnak vissza + egy idővonal-bejegyzést `_append_timeline(state, "<step>", payload)`-lal.
- **Új node**: vedd fel a `graph.py` éleihez, ÉS adj hozzá címet+magyarázatot a `frontend/src/lib/agentSteps.ts` `STEP_META`-hoz, különben a UI a nyers angol lépésnevet mutatja.

## PII és forrás-jelölők
- Ügyfél-felé menő szövegből **el kell távolítani a `[Sn]` jelölőket** (`strip_source_markers`) — ez az approve-úton (`case_service`) és a `prepare_unmask`-ban történik.
- **Soha** ne kerüljön maszkolatlan PII logba, trace-be, promptba vagy teszt-fixture-be.

## Tesztelés
- `tests/conftest.py` autouse fixture **offline-ra kényszeríti az OpenAI-t** (üres kulcs). LLM-utat igénylő teszt **opt-inel**: `monkeypatch.setattr(settings, "openai_api_key", "sk-test")` + `monkeypatch.setattr(<modul>, "chat_json", ...)`.
- **Strukturális assertek** (mezők, citationök, flagek, `*_mode`), **nem** teljes-szöveg snapshot. TDD; minden bughoz reprodukáló regressziós teszt.
- Egy **ismert, független** bukó teszt: `test_settings_have_local_qdrant_defaults` (a lokális `.env` `OPENAI_EMBED_DIM=512` miatt) — ez nem a kódunk.

## Frontend
- One design tokenek: `docs/design-export/tokens.css` + `tailwind.tokens.js`; Tailwind `one-*` osztályok. Named exportok. `tsc --noEmit` + `npm run build` legyen tiszta.

## Git
- **Ne commitolj `main`-re** — dolgozz ágon. Kis, gyakori commitok. Commit-trailer: `Co-Authored-By: Claude ...`.

## Terminológia
`eszkaláció` (ne „emelés"); kivétel a `díjemelés` üzleti kategória. Lásd guardrails §12.

## Hasznos repo-skillek és parancsok
- Skillek (`.claude/skills/`): `add-llm-call`, `add-agent-node`, `rag-pipeline`.
- Parancsok (`.claude/commands/`): `/run`, `/test`, `/pii-check`.
