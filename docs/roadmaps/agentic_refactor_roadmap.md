# Agentic/RAG réteg egyszerűsítési és átláthatósági roadmap

## Cél

A jelenlegi agentic folyamat működőképes, de több regresszió abból fakadt, hogy az LLM-hívások, determinisztikus fallbackek, sender identity kezelés, retrieval pipeline és frontend/backend szerződések több helyen szétszórva élnek. A cél nem egy nagy újraírás, hanem fokozatos, tesztekkel védett egyszerűsítés.

## Javasolt lépések

### 1. Agent node-ok vékonyítása

Az `agent/nodes.py` jelenleg orchestration, üzleti logika, fallback kezelés és timeline payload építés keveréke. A node-ok maradjanak csak koordinátorok, az üzleti döntések kerüljenek backend service-ekbe.

Javasolt bontás:

- `language_service.detect(...)`
- `identity_service.load_context(...)`
- `classification_service.classify(...)`
- `rag_service.retrieve_for_case(...)`
- `approval_service.prepare_preview(...)`

Elvárt eredmény: a LangGraph lépései gyorsan olvashatók, a tesztek pedig service-szinten célzottabbak.

### 2. Központi LLM boundary réteg

Az LLM-hívások jelenleg több modulban élnek: classify, query rewrite, escalation, synthesis, verify. Ezeket érdemes egységes határfelület alá rendezni.

Javasolt modul: `backend/llm_tasks.py`

Javasolt függvények:

- `classify_message_llm(...)`
- `rewrite_query_llm(...)`
- `suggest_escalation_llm(...)`
- `synthesize_answer_llm(...)`
- `verify_grounding_llm(...)`

Minden LLM task egységes eredményformát adjon:

```python
{
    "mode": "llm" | "rule" | "template" | "heuristic" | "failed",
    "result": ...,
    "error": None | "...",
}
```

Elvárt eredmény: a fallbackek auditálhatók, a timeline-ban látszik, mikor történt LLM-hiba vagy szabályalapú visszaesés.

### 3. Backend enumok a módokhoz

A backend jelenleg stringekkel dolgozik több kritikus módnál. Érdemes központi konstansokat vagy enumokat bevezetni.

Javasolt enumok:

- `GenerationMode.LLM`
- `GenerationMode.TEMPLATE`
- `GenerationMode.INSUFFICIENT`
- `VerifyMode.LLM`
- `VerifyMode.HEURISTIC`
- `ClassifyMode.LLM`
- `ClassifyMode.RULE`

Elvárt eredmény: kevesebb typo, stabilabb frontend/backend szerződés, könnyebb tesztelés.

### 4. Sender identity modul

A korábbi előzménykezelési bug oka az volt, hogy a case-lokális mask token (`[MASK_EMAIL_1]`) és a stabil sender key kezelése szétszóródott. Ezt egyetlen modulba kell zárni.

Javasolt modul: `backend/sender_identity.py`

Javasolt felelősségek:

- maskolt sender megjelenítési értéke
- stabil `sender_email_key` képzése
- history lookup engedélyezése vagy tiltása
- régi DB sorok backfill támogatása

Fontos szabály: reusable mask token alapján tilos cross-case historyt keresni.

### 5. Retrieval pipeline explicit fázisokra bontása

A retrieval jelenleg több fázist egy függvényben kapcsol össze: Qdrant/local search, sparse/dense score, category boost, numeric boost, sibling merge, reference closure, parent context.

Javasolt pipeline:

1. query preparation
2. candidate retrieval
3. reranking and boosting
4. structural expansion
5. reference resolution
6. final source packaging

Elvárt eredmény: ha "nincs ÁSZF-fedezet" történik, könnyebb megmondani, hogy query, retrieval, boost, mandatory ref vagy synthesis szinten romlott el.

### 6. Egységes timeline séma

A timeline jelenleg node-onként eltérő payloadot használ. A debug és frontend értelmezhetőség érdekében legyen közös séma.

Javasolt mezők:

```python
{
    "step": "...",
    "mode": "rule|llm|template|heuristic|hybrid",
    "status": "ok|fallback|warning|failed",
    "counts": {},
    "warnings": [],
    "summary": "...",
}
```

Elvárt eredmény: a jobb oldali agent-idővonal nem csak eseménylista, hanem valódi diagnosztikai felület.

### 7. `synthesize_answer` bontása

A `backend/draft.py::synthesize_answer()` túl sok felelősséget visz: source építés, prompt építés, LLM hívás, fallback, citation validáció, email/copilot formázás.

Javasolt bontás:

- `build_sources(policy_map)`
- `build_synthesis_prompt(...)`
- `run_synthesis_llm(...)`
- `normalize_synthesis_result(...)`
- `build_template_fallback(...)`
- `build_insufficient_result(...)`

Elvárt eredmény: a generálási regressziók kisebb felületen jelentkeznek, és célzottabban tesztelhetők.

### 8. Erősebb API contract tesztek

A jelenlegi frontend contract tesztek részben string-keresésen alapulnak. Ezt érdemes valódi endpoint payload tesztekkel kiegészíteni.

Kiemelt endpointok:

- `GET /cases/{id}`
- `GET /history`
- `POST /agent/run`
- `POST /cases/process`

Kiemelt mezők:

- `sender_email_key`
- `sender_email_display`
- `draft.generation_mode`
- `draft.sources`
- `timeline[].output`
- `history.items`
- `history.is_repeated`

Elvárt eredmény: frontend regressziók hamarabb buknak CI-ban.

### 9. Trace és derived data elkülönítése

A kódváltozások mellett gyakran megjelennek trace, derived report és timestamp-only config diffs. Ezek rontják a review olvashatóságát.

Javaslat:

- runtime trace fájlok kerüljenek gitignore alá vagy külön artifact könyvtárba
- generated timestamp-only diffek ne keveredjenek kód PR-ba
- diagnosztikai script maradjon ideiglenes vagy külön `scripts/diagnostics/` mappában dokumentáltan

Elvárt eredmény: könnyebb review, kisebb esély véletlen adatváltoztatás commitolására.

### 10. Golden case regressziós készlet

Legyen kicsi, gyorsan futó end-to-end regressziós készlet a kritikus agent/RAG esetekre.

Javasolt golden case-ek:

- számlázási panasz normál happy path
- hibabejelentés normál happy path
- szerződésfelmondás
- ismétlődő panasz azonos sender key alapján
- különböző feladók azonos `[MASK_EMAIL_1]` tokennel
- LLM outage forrásokkal, template fallbackkel
- nincs forrás, valódi insufficient
- query rewrite LLM hiba, rule fallback

Elvárt eredmény: agent/RAG változtatás előtt és után gyorsan mérhető, hogy a fő üzleti útvonalak nem sérültek.

## Javasolt megvalósítási sorrend

1. Sender identity modul és további regressziós tesztek.
2. Backend enumok és frontend/backend generation-mode szerződés tisztítása.
3. `synthesize_answer` bontása kisebb függvényekre.
4. Egységes timeline séma bevezetése.
5. LLM boundary réteg kialakítása.
6. Retrieval pipeline fázisokra bontása.
7. Golden case regressziós készlet hozzáadása.
8. Trace/derived data kezelés tisztítása.

## Kockázatok és kontrollok

- Minden lépéshez előbb regressziós teszt készüljön.
- Ne legyen egyszerre több viselkedésváltozás egy PR-ban.
- A fallback módok látszódjanak a timeline-ban és audit payloadban.
- Az LLM-hívások ne tudjanak szabályalapú compliance kapukat lazítani.
- A sender identity esetében a mask token soha ne legyen cross-case azonosító.

