# Copilot orchestrator — nem-determinisztikus agent design

> Státusz: jóváhagyott design (brainstorming kimenet). Dátum: 2026-06-09.
> Következő lépés: implementációs terv (writing-plans).

## 1. Cél és kontextus

A **Copilot chat** (`frontend/src/screens/Copilot.tsx`) jelenleg ugyanazt az `/agent/run`
végpontot hívja, mint a Bejövő ügyek — tehát a **lineáris** `agent/graph.py` pipeline-t.
Ez az ügyfél-üzenet egyirányú feldolgozására való, nem az ügyintézővel folytatott,
több fordulós párbeszédre.

A cél: a Copilot chatet **teljesen különálló ágra** vinni, ahol egy **nem-determinisztikus,
orchestrator-vezérelt** agent fut. Az orchestrator egy LLM, amely körönként eldönti,
hogy melyik subagentet hívja, visszakérdez, vagy végleges választ ad. A lineáris inbox
pipeline **érintetlen marad**.

### Döntések (brainstorming)

- **Cél (széles asszisztens):** ügyfél-válasz draft + belső tudás-Q&A +
  döntéstámogatás/eszkaláció + ügyfél-kontextus lekérdezés.
- **Orchestráció:** LLM tool-calling ciklus — a subagentek "tool"-ként expónáltak.
- **Szeparáció:** külön orchestráció, **közös üzleti logika** — a subagentek a meglévő,
  bizonyított backend függvényeket/service-eket hívják eszközként. Nincs kódduplikáció,
  a PII/forrásolás/guardrail egy helyen marad.

### Nem cél (YAGNI)

- A lineáris inbox pipeline átírása vagy lecserélése.
- Önálló retrieval/draft/verify újraimplementálás a Copilot ághoz.
- Ügyféllel közvetlenül kommunikáló autonóm agent — ez továbbra is human-in-the-loop,
  ügyintézői copilot.

## 2. Subagent-készlet

Az orchestrator LLM; a subagentek "tool"-ok, amiket meghívhat. Mindegyik subagent egy
meglévő backend service-t/függvényt csomagol be (vékony adapter), egységes
timeline-bejegyzést és `*_mode` flaget ad vissza, és kizárólag **maszkolt** szövegen dolgozik.

### Mag-subagentek

| # | Subagent | Felelősség | Becsomagolt backend |
|---|----------|-----------|---------------------|
| 1 | **Tudás-kereső** (ÁSZF) | Fókuszált keresőkérdés + ÁSZF-chunkok `[Sn]` forrásjelölőkkel. A tudás-Q&A és a draft-megalapozás közös alapja. | `query_rewrite.rewrite_query` + `retrieval.retrieve` + `policy_map.build_policy_map` |
| 2 | **Kategorizáló** | Panaszkategória/altípus + konfidencia. Az eszkaláció és a keresés bemenete. | `classify.classify_message` |
| 3 | **Eszkalációs tanácsadó** | "Eszkaláljam? Kockázat? Miért?" — szabály + LLM javaslat összefésülve. | `escalation.decide_escalation` + `llm_escalation_suggestion` + `merge_escalation` |
| 4 | **Ügyfél-kontextus** | Korábbi ügyek, előzmény-összegzés, ügyfél-rekord — maszkoltan. | `history.get_history` + `MockCustomerDirectory.lookup_by_email` |
| 5 | **Válaszfogalmazó** (draft) | Ügyfél-felé menő választervezet a policy-map + chunkok alapján, citationökkel. | `draft.synthesize_answer` |
| 6 | **Forrás-ellenőrző** (grounding) | A draft minden állítása megalapozott-e a hivatkozott chunkban; lefedetlen részek jelölése. | `verify.verify_draft` |

### Kiegészítő subagent (opcionális)

| # | Subagent | Felelősség | Becsomagolt backend |
|---|----------|-----------|---------------------|
| 7 | **Ügy-művelet** | Beszélgetésből ügyet nyit / akciókat javasol. | `suggest_actions` + `case_service` / `createCase` |

### Szándékosan NEM subagent

- **Visszakérdezés** az ügyintézőnek — az orchestrator natív képessége: ha kevés az infó,
  kérdéssel válaszol. Ez a nem-determinizmus egyik megnyilvánulása.
- **Maszkolás / forrásjelölő-csökkentés** — nem subagent, hanem a ciklust körülvevő
  kötelező kapu (lásd §3).

### Példa nem-determinisztikus folyam

Panasz bemásolva → *Kategorizáló* → *Ügyfél-kontextus* (van-e előzmény) → *Tudás-kereső*
→ eszkalációs trigger észlelve → *Eszkalációs tanácsadó* → mivel eszkaláció kell, NEM
fogalmaz ügyfél-draftot, hanem összefoglal és tanácsot ad. Egy másik körben (egyszerű
ÁSZF-kérdés) lehet, hogy csak a *Tudás-keresőt* hívja. A lépések és sorrendjük a
helyzettől függenek — ez a lényegi különbség a lineáris pipeline-hoz képest.

## 3. Orchestrator-ciklus és kötelező guardrail-kapuk

```
[ügyintéző üzenet]
      │
      ▼
  MASZKOLÓ KAPU (belépés) — kötelező, nem subagent
  mask_text(session_id, üzenet) → csak maszkolt szöveg megy tovább
      │
      ▼
  ORCHESTRATOR (LLM, chat_json)  ◄─────────────┐
  Dönt: subagentet hív / visszakérdez / kész   │ tool-eredmény
      │ tool-hívás                             │ visszacsatolva
      ▼                                        │
  [subagent fut a maszkolt szövegen] ──────────┘
  (timeline-bejegyzés + *_mode flag)
      │  ha "kész"
      ▼
  KILÉPÉSI KAPU — kötelező
  unmask + strip_source_markers CSAK az ügyfél-felé menő szövegen
      │
      ▼
[válasz: szöveg + források + audit-timeline]
```

### Kötelező guardrailek (guardrails / CLAUDE.md miatt nem opcionálisak)

1. **Maszkolás belépéskor.** Az orchestrator és MINDEN subagent kizárólag maszkolt
   szövegen dolgozik. PII soha nem kerül LLM-promptba, tool-hívásba, logba, timeline-ba.
   A maszk-térképet a session `session_id`/`case_id` adja (a Copilot már most `CHAT-<uuid>`).
2. **Forrásjelölő-eltávolítás kilépéskor.** `strip_source_markers` csak az ügyfél-felé
   szánt draftnál. A tudás-Q&A válaszban a `[Sn]` megmaradhat (belső, kattintható forrás).
3. **Determinisztikus fallback.** Ha `llm_available()` hamis, az orchestrator nem omlik
   össze: egyszerű, szabály-alapú útvonalra esik (pl. csak Tudás-kereső + sablon-válasz).
   Minden subagent megtartja `*_mode` flagjét (`classify_mode`, `generation_mode`,
   `verify_mode`, `escalation_mode`); új flag: `orchestrator_mode` (`llm` / `fallback`).
4. **Audit-timeline.** Minden orchestrator-döntés és subagent-hívás bekerül egy timeline-ba
   (mint `_append_timeline`), hogy a futás auditálható és a frontenden megjeleníthető legyen.
   Új subagent → `STEP_META` bejegyzés a `frontend/src/lib/agentSteps.ts`-be.
5. **Ciklus-korlát.** Max. iterációszám (pl. 6–8 tool-hívás) és időkorlát a végtelen
   ciklus ellen; a korlát elérése naplózva és a timeline-on jelezve.
6. **Hibák nem nyelődnek el.** `try/except` + `logger.exception(...)` + fallback minden
   LLM/tool-hívásnál (a néma fallback korábban regressziókat fedett el).

### Állapot a fordulók közt

A chat több fordulós: a maszk-térkép, a már lehívott chunkok és a kumulatív timeline a
session élettartamára megmaradnak (nem kérünk le mindent újra minden üzenetnél).

## 4. Kódszervezés

Új csomag a lineáris `agent/graph.py` **mellett**, nem helyette.

| Fájl | Felelősség |
|------|-----------|
| `agent/copilot/orchestrator.py` | LLM tool-calling ciklus: `chat_json` + tool-spec; döntés (subagent / visszakérdezés / válasz); ciklus-korlát; `orchestrator_mode`; hibakezelés. |
| `agent/copilot/subagents.py` | A 6+1 subagent mint vékony adapter; backend service-t hív, egységes timeline + `*_mode`. |
| `agent/copilot/tools_spec.py` | Tool-sémák (név, leírás, JSON-paraméterek), amiket az orchestrator LLM lát. |
| `agent/copilot/session.py` | Több fordulós session-állapot: maszk-térkép ref, beszélgetés-előzmény, chunk-cache, kumulatív timeline. |
| `agent/copilot/runner.py` | `run_copilot_turn(session_id, message, history)` — kapu → ciklus → kapu → válasz. |

**Backend végpont:**
- `backend/api/copilot.py` — új router: `POST /copilot/chat` (a `/agent/run` mellett, azt érintetlenül hagyva).
- `backend/api/contracts.py` — `CopilotChatRequest` / `CopilotChatResponse` (session_id, message, history → reply, sources, timeline, modes).

**Frontend:**
- `frontend/src/screens/Copilot.tsx` — átáll `api.agentRun`-ról `api.copilotChat`-re; küldi a session_id-t + előzményt.
- `frontend/src/lib/api.ts` + `types.ts` — új `copilotChat` metódus és típusok.
- `frontend/src/lib/agentSteps.ts` — `STEP_META` kiegészítés az új subagent-lépésnevekkel.

**Elv:** a subagent-adapterek nem tartalmaznak üzleti logikát — csak service-t hívnak és
timeline-t formáznak. Így a lineáris graph node-jai és a Copilot subagentjei ugyanazt a
forrást hívják (lásd §5 refactor #1).

## 5. Előfeltétel-refactor (sorrend)

A [agentic_refactor_roadmap.md](../../agentic_refactor_roadmap.md) pontjai erősen
átfedik az új agent alapjait. Ajánlott sorrend: **célzott köztes út** — nem az egész
refactor előbb, és nem is a nyers alapra épített agent.

### A) Először a "közös varrat" refactor-részhalmaza (az új agent alá esik)

1. **Roadmap #10 + #8** — golden case-ek és endpoint contract tesztek *előbb*, hogy a
   refactor és az új agent is védve legyen.
2. **Roadmap #1** — a subagentek által hívott üzleti logikát tiszta service-ekbe emelni
   (`rag_service`, `classification_service`, `approval_service`, …).
3. **Roadmap #2** — központi LLM-boundary (`backend/llm_tasks.py`) egységes
   `{mode, result, error}` formával → a subagent-wrapperek egységesek lesznek.
4. **Roadmap #3 + #6** — mode-enumok és egységes timeline-séma, *mielőtt* a
   frontend-szerződésbe égnek.

### B) Utána az új Copilot-orchestrator

A letisztult varratra építve a subagentek vékony adapterek a service-ek fölött.

### C) Végül a maradék refactor opportunista módon

Roadmap #7 (`synthesize_answer` bontás), #5 (retrieval fázisok), #4 (sender identity),
#9 (trace/diagnosztika higiénia) — ezek nem blokkolják az agentet.

**Indok:** a nyers, kevert `nodes.py`-logikára épített subagentek átöröklenék a
szétszórtságot (kétszer fizetett refactor, frontend-churn a `*_mode`/timeline körül).
Az egész refactor előrevétele viszont fölösleges késleltetés, mert #5/#7/#4/#9 nem
feltétele az agentnek.

## 6. Tesztelés

A repo mintái szerint (`tests/conftest.py` offline-kényszer, strukturális assertek):

- **Orchestrator routing:** adott bemenetre helyes tool-választás (LLM mockolva a
  `chat_json`-on); strukturális assert a hívott subagentre, nem teljes-szöveg snapshot.
- **Guardrail-kapuk:** a maszkoló/kilépő kapu sosem enged PII-t a timeline-ba/válaszba;
  `strip_source_markers` az ügyfél-draften lefut.
- **Fallback:** alapból offline → `orchestrator_mode == "fallback"` út; LLM-út opt-in
  `monkeypatch.setattr(settings, "openai_api_key", "sk-test")` + `chat_json` mock.
- **Mode-flagek:** minden subagent beállítja a saját `*_mode`-ját.
- **Golden case-ek** (roadmap #10) az orchestrator tipikus folyamaira.

## 7. Nyitott pontok az implementációs tervhez

- A `chat_json` JSON-object módja vs. natív tool-calling API — a tool-spec hogyan
  fordul `chat_json` promptra (a repo a `chat_json`-t használja minden LLM-hívásra).
- A session-állapot tárolása: memóriában a kérés élettartamára vs. perzisztált
  (a chat több fordulós a frontenden, de a backend stateless híváson megy ma).
- A `/copilot/chat` végpont auditálása: kell-e `agent_runs`-szerű perzisztálás a
  Copilot-futásokhoz.
