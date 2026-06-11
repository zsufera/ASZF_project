# Agent workflow és AI/szabályalapú elválasztás

## Pipeline áttekintés

A LangGraph agent (`agent/graph.py`) **lineáris, feltétel nélküli pipeline** — nincs elágazás, nincs ciklus. Minden node részleges state-et ad vissza és timeline-bejegyzést fűz hozzá.

```
mask → classify → retrieve → policy_map → draft → verify → escalation
```

## Node-ok: AI vs. szabályalapú

| Node | AI (LLM) | Szabályalapú | Fallback | Mode mező |
|------|----------|-------------|----------|-----------|
| **mask** | — | Presidio NER + regex | — | — |
| **classify** | `chat_json(CLASSIFY_SYSTEM, ...)` | Kulcsszó-egyezés + konfidencia-formula | LLM hiba → szabályalapú | `classify_mode` |
| **query_rewrite** | `chat_json(REWRITE_SYSTEM, ...)` | Kategória-kulcsszavak | LLM hiba → szabályalapú | — |
| **retrieve** | Embedding (OpenAI) + Qdrant | BM25 sparse + determinisztikus embedding | API hiba → lokális hybrid | `retrieval_mode` |
| **policy_map** | — | YAML-szabálytérkép (`config/policies.yaml`) | — | — |
| **draft** | `chat_json(SYNTH_SYSTEM, ...)` | Sablon-alapú válaszlevél | LLM hiba → sablon | `generation_mode` |
| **verify** | `chat_json(VERIFY_SYSTEM, ...)` (LLM judge) | Token-átfedés heurisztika | LLM hiba → heurisztika | `verify_mode` |
| **escalation** | `chat_json(ESCALATION_SYSTEM, ...)` | Szabályalapú trigger-lista | LLM hiba → szabályalapú | `escalation_mode` |

## Fallback mechanizmus

Minden LLM-hívó node a következő mintát követi:

1. Ellenőrzi `llm_available()` → ha `false`, azonnal szabályalapú mód
2. `try`: LLM-hívás `chat_json()` segítségével
3. `except`: `logger.exception(...)` + szabályalapú fallback
4. A `*_mode` mező jelzi a válaszban, melyik út futott (`"llm"`, `"rule"`, `"template"`, `"heuristic"`)

Ez azt jelenti, hogy **a rendszer OpenAI API-kulcs nélkül is teljes mértékben működik** determinisztikus módban.

## Human-in-the-loop (HITL) pont

```
                              ┌──────────────┐
  agent pipeline ──────────▶  │ draft kész   │
                              └──────┬───────┘
                                     │
                              ┌──────▼───────┐
                              │ ügyintéző    │  ◀── szerkesztés, módosítás
                              │ jóváhagyás   │
                              └──────┬───────┘
                                     │
                           ┌─────────▼─────────┐
                           │ approve_draft()   │  ◀── RBAC ellenőrzés
                           │ unmask (PII)      │  ◀── audit log
                           │ strip_source_     │
                           │   markers()       │  ◀── [Sn] jelölők eltávolítása
                           └─────────┬─────────┘
                                     │
                              ┌──────▼───────┐
                              │ ügyfélnek    │
                              │ küldött      │
                              │ válasz       │
                              └──────────────┘
```

A `POST /unmask` és `POST /cases/approve` RBAC és audit alatt áll (`security/rbac.py`, `backend/audit_service.py`).

## Prompt-verziókezelés

Minden rendszerprompt külön fájlban él a `prompts/` mappában:

| Fájl | Használó modul |
|------|---------------|
| `prompts/preamble.txt` | `backend/llm.py` — minden LLM-hívás elé fűzött biztonsági prefixum |
| `prompts/classify.txt` | `backend/classify.py` |
| `prompts/draft_synthesize.txt` | `backend/draft.py` |
| `prompts/verify.txt` | `backend/verify.py` |
| `prompts/escalation.txt` | `backend/escalation.py` |
| `prompts/query_rewrite.txt` | `backend/query_rewrite.py` |
| `prompts/orchestrator.txt` | `agent/copilot/orchestrator.py` |
| `prompts/judge.txt` | `eval/llm_judge.py` |

## AI-használat indokoltsága

A szabályalapú fallback **létezik és működik** — ez teszi lehetővé az összehasonlítást. Az `eval/` evaluation harness mérhető különbséget mutat az LLM és a szabályalapú út között:

- **Osztályozás**: a szabályalapú kulcsszó-egyezés nem kezel szinonimákat és többértelmű szöveget
- **Válasz-draft**: a sablon strukturált, de nem személyre szabott és nem kontextusfüggő
- **Groundedness**: a token-átfedés heurisztika nem kezel parafrázist (a szó szerinti idézet-keresés hamis negatívokat ad)
- **Eszkaláció**: a trigger-lista fix; az LLM felismeri az implicit eszkalációs jeleket is

Tehát az AI **mérhető értéket ad** a szabályalapú rendszerhez képest, de a szabályalapú mód biztosítja a működést LLM nélkül is.
