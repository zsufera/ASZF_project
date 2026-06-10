# CLAUDE.md - operatív kontextus Claude-nak

> Ez a fájl Claude Code számára ad technikai/operatív kontextust.
> A termék- és architektúra-elvek kötelező forrása: [docs/specs/FEJLESZTESI_GUARDRAILS.md](docs/specs/FEJLESZTESI_GUARDRAILS.md). Konfliktus esetén a felhasználó kérése és a guardrails irányadó.

## Mi ez

Belső ügyintézői copilot telekom ügyfélszolgálatra: ÁSZF-forrásolt válasz-draft, eszkalációs döntéstámogatás, audit és human-in-the-loop jóváhagyás. Nem ügyféllel közvetlenül kommunikáló autonóm agent.

## Repo-térkép

- `backend/` - FastAPI API (`main.py`) és üzleti logika: `llm.py`, `draft.py`, `classify.py`, `escalation.py`, `verify.py`, `policy_map.py`, `retrieval.py`, `masking.py`, `case_service.py`, `audit_service.py`, `eval_service.py`.
- `backend/api/` - routerek: agent, cases, copilot, history, knowledge, contracts.
- `backend/services/` - service-határok: approval, classification, RAG.
- `agent/` - LangGraph állapotgép: `graph.py` lineáris pipeline, `nodes.py`, `state.py`, `runner.py`.
- `frontend/` - aktív React + TypeScript + Tailwind + Vite SPA. Fő helyek: `src/screens`, `src/components`, `src/components/case`, `src/lib`, `src/state`.
- `preprocessing/` - ingest pipeline: manifest, parse, index, embedding, derive_params, sample email generálás, smoke CLI-k.
- `eval/` - referencia-mentes kiértékelés.
- `demo/` - automatizált demó-szcenáriók.
- `integrations/` - mock adapterek: case store, email adapter, customer directory.
- `legacy/ui/` - Streamlit UI, csak legacy referencia.
- `docs/` - rendezett dokumentáció; belépési pont: `docs/README.md`.

## Dokumentációs rend

- `docs/specs/` - üzleti/technikai/frontend/contract/prompt specek és `FEJLESZTESI_GUARDRAILS.md`
- `docs/roadmaps/` - UI, RAG, non-UI, agentic és kódbázis roadmapek
- `docs/governance/` - DPIA és compliance checklist
- `docs/operations/` - demo script és bugfix/quality operatív tervek
- `docs/superpowers/` - agentic implementációs tervek és design specek
- `docs/archive/` - leváltott vagy történeti dokumentáció

## Futtatás Windows alatt

```powershell
# Backend API, fejlesztéshez
uvicorn backend.main:app --reload

# React frontend
cd frontend
npm install
npm run dev

# Egyfolyamatos API + buildelt SPA
.\start.ps1
```

PowerShellben ne használj `&&` láncot; `;` vagy külön sor kell. Backend Python-kód módosítása után Windows-on indítsd újra az uvicorn folyamatot, mert a reload nem mindig megbízható.

## Ellenőrzések

```powershell
python -m pytest tests/ -q
cd frontend
npx tsc --noEmit
npm run build
python scripts/run_quality_gate.py
```

A `tests/conftest.py` offline OpenAI-környezetet kényszerít. LLM-út teszteléséhez explicit monkeypatch kell: `settings.openai_api_key = "sk-test"` és az érintett modul `chat_json` függvényének stubolása.

## LLM-hívások

- Minden LLM-hívás a `backend/llm.py::chat_json(system, user)` határon menjen át, JSON-object módban.
- Mindig használd az `llm_available()` kaput.
- Fallback esetén determinisztikus vagy sablonos viselkedés kell, és legyen `*_mode` mező (`classify_mode`, `generation_mode`, `verify_mode`, `escalation_mode`).
- Külső híváshibát ne nyelj el némán: `logger.exception(...)` + fallback.
- `gpt-5`, `o1`, `o3`, `o4` típusú modelleknél ne vezess vissza feltétlen `temperature=` paramétert; a meglévő `_supports_custom_temperature()` logikát kell tiszteletben tartani.
- Promptba csak maszkolt szöveg kerülhet; a `SYSTEM_PREAMBLE` a bejövő ügyfélszöveget adatként kezeli.

## Agent-szabályok

- `agent/graph.py` lineáris: nincs feltételes él vagy ciklus.
- Node-ok `agent/nodes.py` alatt részleges state-et adnak vissza, és timeline-bejegyzést fűznek hozzá.
- Új agent node esetén frissítsd a `frontend/src/lib/agentSteps.ts` `STEP_META` térképét is, különben a UI nyers step nevet mutat.

## PII és forrásjelölők

- Maszkolatlan PII nem kerülhet logba, trace-be, promptba, audit payloadba vagy teszt fixture-be.
- Ügyfél felé menő szövegből el kell távolítani a `[Sn]` forrásjelölőket (`strip_source_markers`). Ez az approve-úton és a `prepare_unmask` folyamatban történik.
- `/unmask` és approve műveletek RBAC és audit alatt állnak.

## Frontend

- Aktív UI: `frontend/`, nem `legacy/ui/`.
- One design tokenek: `docs/archive/design-export/tokens.css` és `docs/archive/design-export/tailwind.tokens.js`.
- Named exportokat használj, és futtasd: `npx tsc --noEmit`, `npm run build`.

## Git

- Ne commitolj közvetlenül `main`-re.
- Kis, jól körülhatárolt commitok.
- Commit trailer: `Co-Authored-By: Claude ...`

## Terminológia

Használd: `eszkaláció`, `eszkalált ügy`, `eszkalációs trigger`, `eszkalációs döntés`. Ne használd eszkalációs értelemben az `emelés` szót; kivétel a `díjemelés` üzleti kategória.

## Hasznos repo-skillek és parancsok

- Skillek: `.claude/skills/add-llm-call`, `.claude/skills/add-agent-node`, `.claude/skills/rag-pipeline`
- Parancsok: `.claude/commands/run.md`, `.claude/commands/test.md`, `.claude/commands/pii-check.md`
