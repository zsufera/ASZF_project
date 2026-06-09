# UI-roadmap — funkcionális fejlesztési lehetőségek

> **Cél:** nagyobb, funkcionalitásbeli UI-fejlesztések specifikációja a React frontendhez (`frontend/`), a meglévő FastAPI backendre illesztve. Nem stílus/kozmetika: a use-case magját (auditálható, forrásolt, ember-kontrollált ügyintézői copilot) erősítő, működő funkciók.
> **Forma:** stratégiai roadmap, tételenként implementálható spec-vázlat. Minden tétel külön implementációs tervvé (`docs/superpowers/plans/`) bontható.
> **Kapcsolódó:** [`docs/archive/design-export/`](archive/design-export/) (archivált One arculat/tokenek), [`frontend/UX-DECISIONS.md`](../frontend/UX-DECISIONS.md), [`docs/rag-roadmap.md`](rag-roadmap.md), [`FEJLESZTESI_GUARDRAILS.md`](../FEJLESZTESI_GUARDRAILS.md) (§7 UI guardrailek).
> **Frissítve:** 2026-06-09, a Tier 1-3 implementáció után.

---

## 0. Jelenlegi állapot (kódra hivatkozva)

**Képernyők** (`frontend/src/screens/`): `Login`, `Inbox`, `CaseWorkstation`, `NewCase`, `Copilot`, `Postal`, `Evaluation`, `Supervisor`.
**Komponensek** (`frontend/src/components/`): `AppShell`, `IconNav`, `TopHeader`, `AgentTimeline` + `TimelineStep`, `SourceCard`/`RichSourceCard`, `InlineAnswer`, `DraftEditor`, `ProcessingIndicator`, `CaseBadgeRow`, `HistoryCard`, `CustomerCandidate`, `KpiCard`, `Modal`, `Toast`, `OfflineBanner`, valamint a `components/case/` alatti CaseWorkstation-panelek.
**API-réteg** (`frontend/src/lib/api.ts`): bekötve a copilot/ügy/draft/approve/feedback/history/customer-lookup/eval/supervisor/audit-case/governance-purge. A `runEval`, `setHumanScore`, `evalBaseline`, `getAuditCase` és `purgeGovernance` már létezik a frontend API-ban.

### Aktuális, kihasználatlan vagy részben kihasznált backend-erő

| Backend-képesség | Végpont / adat | UI-állapot |
|---|---|---|
| Audit-esemény stream | `/audit/events` | be van kötve a Supervisor audit-keresőbe |
| Audit-completeness ügyenként | `/audit/completeness/{id}` | be van kötve CaseWorkstation és Supervisor nézetben |
| Ügy-audit (iterációk) | `/audit/cases/{id}` | be van kötve a CaseWorkstation audit-panelbe |
| Observability trace-ek | `/observability/traces` | be van kötve a Supervisor trace viewerbe |
| Acceptance-kapu | `/acceptance/run` | be van kötve az Evaluation acceptance panelbe |
| Governance/retention purge | `/governance/purge` | Supervisor dry-run/execute panellel használható |
| Újraindexelés | `/reindex` | **nincs bekötve** |
| Verify claim-szintű kimenet | `/verify` + `agent_state.verify.claims` | megjelenik a draft-panel grounding részében |
| Retrieval-provenance | `retrieval_source`, `unresolved_refs`, score | provenance badge, score és unresolved panel megjelenik |
| Eval baseline és human score | `/eval/baseline`, `/eval/human-score` | emberi diff, score összegzés és drill-down nézet elkészült |

---

## 1. Tervezési alapelvek

1. **Backend-elsőbbség hasznosítása:** ahol a végpont már létezik, az UI-érték magas és gyors.
2. **A forrásoltság/audit a use-case magja** (guardrails §2, §7): minden nagyobb UI-fejlesztés ezt erősítse, ne hígítsa.
3. **HITL & RBAC:** az ügyfél felé menő vagy érzékeny műveletek (unmask, approve, purge, automata mód) szerepkör-kötöttek és auditáltak maradjanak.
4. **Operátori hatékonyság:** egész nap használható, sűrű, billentyűvel is vezérelhető munkafelület; mentett nézetek, gyors keresés, alacsony kattintásszám.
5. **One arculat & tokenek:** archivált forrás `docs/archive/design-export/tokens.css` + `tailwind.tokens.js`, `one-*` osztályok; named exportok; `tsc --noEmit` + `npm run build` tiszta.
6. **a11y:** `aria-*`, fókuszgyűrű, billentyű-elérhetőség, stabil méretezés.
7. **Offline-biztos:** az `OfflineBanner` mintára minden új nézet kezelje a backend-hiányt.

---

## 2. Roadmap tételenként

### Tier 1 — nagy érték, a backend már létezik vagy majdnem teljes

#### A — Forrásoltság & provenance-munkafelület

- **Gap:** a retrieval-provenance és a verify claim-szintű kimenete nem jelenik meg; a válasz-forrás kapcsolat most főleg inline `[Sn]` chipekig és source-scrollig megy.
- **Javaslat:**
  - **Claim-szintű groundedness-kiemelés:** a draft állításai jelölve (megalapozott/nem), hover vagy fókusz esetén a támasztó forrásra ugrással.
  - **Forrás-provenance badge** a `RichSourceCard`-on: `qdrant_semantic`, `hybrid_local`, `reference_closure`, `parent_context`, `auto_merged` emberi címkével + relevancia-score.
  - **Be nem húzható hivatkozások panel:** `retrieval.unresolved_refs` kiemelése a forráspanelben.
  - **Kötelező hivatkozás státusz:** `policy_map.missing_mandatory` látható jelzése a draft mellett, nem csak timeline részletként.
  - **Hivatkozási-gráf mini-nézet** későbbi bővítésként, a `cross_refs` alapján.
- **Backend:** létezik vagy részben létezik (`verify.claims`, `retrieval_source`, `unresolved_refs`, `policy_map`).
- **Frontend:** `lib/types.ts` bővítés (`VerifyClaim`, `retrieval_source`, `unresolved_refs`, `missing_mandatory`), `InlineAnswer`, `RichSourceCard`, `CaseSourcesPanel`, `CaseDraftPanel`.
- **Erőfeszítés:** M. **Kockázat:** alacsony.

#### B — Audit & compliance konzol

- **Gap:** szabályozott, auditálható copilot, de az audit/governance/trace végpontok csak részben vannak UI-ra kivezetve; ahol megjelennek, ott nyers JSON formában.
- **Javaslat:**
  - **Ügy-szintű audit fül** a CaseWorkstationben: idővonal (ki/mikor/mit), PII-hozzáférési napló (unmask/approve), modell/prompt/`aszf_version`, döntési okok (eszkaláció, verify).
  - **Completeness-indikátor** ügyenként: hiányzó auditmezők emberi címkékkel.
  - **Globális audit-nézet** supervisor nav-pontként: esemény-kereső/szűrő `/audit/events` alapján.
  - **Governance/retention panel:** purge dry-run táblázatos előnézet, explicit megerősítés, eredmény audit.
  - **Trace-viewer:** legutóbbi agent futások és hibák visszanézése `/observability/traces` alapján.
- **Backend:** létezik (`/audit/cases/{id}`, `/audit/events`, `/audit/completeness/{id}`, `/governance/purge`, `/observability/traces`).
- **Frontend:** `api.ts` bővítés (`getAuditEvents`, `getAuditCompleteness`, `getTraces`), `screens/Audit.tsx`, `CaseWorkstation` audit-fül, `AuditTimeline`, `PiiAccessLog`, `AuditCompletenessBadge`.
- **Erőfeszítés:** M-L. **Kockázat:** alacsony. **RBAC:** supervisor-only a globális/governance részekhez.

#### C — Evaluation & minőség-dashboard továbbfejlesztése

- **Aktuális állapot:** az Evaluation képernyő már futtat evalt, KPI-kártyákat mutat, exportál JSON-t, és támogat emberi 1-5 pontozást. A baseline diff csak nyers JSON, az acceptance gate nincs bekötve, a gyenge esetek nem elemezhetők jól.
- **Javaslat:**
  - **Baseline-regresszió diff emberi nézetben:** KPI-nként romlott/javult/nincs változás, célértékhez képest.
  - **Bukó-eset drill-down:** egy gyenge eset megnyitása -> kérdés, draft, források, verify claims, hiányzó kötelező hivatkozások.
  - **Acceptance-gate státusz** supervisor vagy Evaluation nézetben (`/acceptance/run`).
  - **Human-score összegzés:** átlag, szórás, alacsony pontszámú esetek listája.
  - **Eval-run visszakeresés:** `getEvalRun` használata korábbi futások megnyitására.
- **Backend:** eval endpointok léteznek; `/acceptance/run` létezik, frontend API-ba még nincs bekötve.
- **Frontend:** `screens/Evaluation` kibővítés, `EvalRegressionDiff`, `EvalCaseDrilldown`, `AcceptanceGatePanel`.
- **Erőfeszítés:** M. **Kockázat:** alacsony.

### Tier 2 — nagy érték, új vagy bővített backend is kell

#### D — Valódi agent-streaming (SSE)

- **Gap:** a `ProcessingIndicator` szimulált és időalapú; a `/agent/run` és `/copilot/chat` szinkron választ ad. A felhasználó nem látja, melyik node tart ténylegesen, és nincs valódi token- vagy lépésstream.
- **Javaslat:** SSE végpont (`/agent/run/stream`, opcionálisan `/copilot/chat/stream`) LangGraph/Copilot eseményekkel: node started/completed, warnings, tool-call observation, draft tokenek. A frontend `EventSource`-szal fogadja, a `ProcessingIndicator` a valós eseményekre vált.
- **Backend:** új streaming endpoint + fallback a szinkron útra.
- **Frontend:** `lib/api.ts` streaming helper, `ProcessingIndicator`, `AgentTimeline`, `Copilot`, `CaseDraftPanel`.
- **Erőfeszítés:** M-L. **Kockázat:** közepes (streaming/hibakezelés, timeout, fallback).
- **Státusz 2026-06-09:** első implementáció elkészült: `/agent/run/stream` SSE endpoint, frontend `streamAgentRun` helper, `start`/`step`/`complete`/`error` eseménykezeléssel. Későbbi bővítés: tényleges LangGraph node-közbeni stream és opcionális `/copilot/chat/stream`.

#### E — Supervisor operációs konzol

- **Gap:** a Supervisor jelenleg KPI + eszkalált sor + audit/purge kezdemény. Nincs valódi munkakiosztás, átvétel, bulk kezelés vagy SLA-operáció.
- **Javaslat:**
  - Ügy **átvétel/kiosztás** (claim/assign).
  - Eszkaláció **jóváhagyás/felülbírálás** indokkal.
  - **SLA-számláló + lejárat-riasztás**, kategória/csatorna szerinti SLA policy alapján.
  - Bulk műveletek (státuszváltás, visszaadás, supervisorhoz rendelés).
  - Supervisor-döntés audit.
- **Backend:** részben létezik (`/cases/status`), de assignee/claim/SLA breach mezők és endpointok új DB-sémát igényelnek.
- **Frontend:** `screens/Supervisor`, `EscalationQueue`, `SlaCountdown`, bulk-akciósáv, assignee filter.
- **Erőfeszítés:** M-L. **Kockázat:** közepes.
- **Státusz 2026-06-09:** első implementáció elkészült: `cases` assignment/claim/SLA mezők, `/cases/claim`, `/cases/assign`, `/cases/release`, auditált claim/assign/release, Supervisor queue tulajdonos- és SLA-oszloppal. Későbbi bővítés: bulk műveletek, assignee filter, kategória/csatorna szerinti SLA policy.

#### F — Copilot session és ügy-handoff UX

- **Gap:** a Copilotból létrehozott ügy azonosítója fül-szintű `sessionStorage`-ban él; a chat session nem perzisztált üzleti munkamenetként, és a handoff nem mutatja, pontosan melyik beszélgetésrészből lett ügy.
- **Javaslat:**
  - Perzisztált Copilot session lista: folytatható beszélgetések.
  - Ügy létrehozásakor előnézet: inbound összefoglaló, csatorna, kiválasztott részletek, javasolt tárgy.
  - Handoff audit: melyik Copilot turnök, források és tool-callok kerültek az ügybe.
  - Chat/telefon külön kontextusjelölés, hogy a Copilot belső segítség, nem ügyfélnek küldött válasz.
- **Backend:** új vagy bővített session store; a UI első verziója lokális állapottal indulhat, de pilothoz perzisztencia kell.
- **Frontend:** `Copilot`, `CopilotSessionList`, `CreateCaseFromCopilotModal`.
- **Erőfeszítés:** M. **Kockázat:** közepes.
- **Státusz 2026-06-09:** első implementáció elkészült: `copilot_sessions`/`copilot_turns` store, session lista, `/copilot/sessions`, `/copilot/sessions/turn`, `/copilot/sessions/handoff`, auditált ügy-handoff és Copilot session oldalsáv. Későbbi bővítés: turn-visszatöltés, handoff preview/modal, kiválasztott részletek szerkesztése.

### Tier 3 — produktivitás / új felületek

#### G — Inbox produktivitás és mentett munkanézetek

- **Gap:** az Inbox szűrők működnek, de nem perzisztensek; nincs mentett nézet, bulk művelet, assignee/SLA oszlop vagy billentyűs listanavigáció.
- **Javaslat:**
  - **Mentett inbox-nézetek:** például „Sürgős + ma lejár”, „Eszkalált”, „Saját ügyek”, „Postai/OCR”.
  - **URL + localStorage szűrő-perzisztencia** a keresés, kategória, státusz, csatorna és rendezés állapotára.
  - **Billentyűs navigáció:** fel/le ügyválasztás, Enter megnyitás, `/` keresés, `p` feldolgozás.
  - **Bulk műveletek:** kijelölés, státuszváltás, supervisorhoz küldés.
  - **SLA/assignee/deduplikáció jelzések** a lista sorain.
- **Backend:** részben új (assignee/dedup/bulk endpointok), az első mentett nézet és billentyűs UX frontend-only lehet.
- **Frontend:** `Inbox`, `SavedViewsBar`, `BulkActionBar`, keyboard hook.
- **Erőfeszítés:** M. **Kockázat:** alacsony-közepes.
- **Státusz 2026-06-09:** első implementáció elkészült: mentett nézetek, localStorage szűrőperzisztencia (`jogos.inbox.filters`), billentyűs lista-navigáció, kijelölés, bulk státuszművelet, SLA/assignee/claim metaadatok az Inbox sorokon. Későbbi bővítés: szerveroldali mentett nézetek, assignee filter, dedup jelzés.

#### H — Command palette és gyorsbillentyűk

- **Javaslat:** `Ctrl/Cmd-K` command palette: ügy megnyitása, feldolgozás indítása, draft mentés/jóváhagyás, eszkaláció, audit nézet, forráskeresés, eval futtatás. A gyakori műveletekhez fix gyorsbillentyűk és tooltipben látható shortcutok.
- **Backend:** többnyire nincs új backend; csak meglévő route-ok és API-hívások összefűzése.
- **Frontend:** `components/CommandPalette`, globális shortcut hook, route/action registry.
- **Erőfeszítés:** S-M. **Kockázat:** alacsony.
- **Státusz 2026-06-09:** első implementáció elkészült: globális `Ctrl+K` command palette, role-alapú route registry, Knowledge/Supervisor/Eval/Copilot gyorsnavigáció.

#### I — Draft power-szerkesztés

- **Aktuális állapot:** van verzióválasztás, szerkesztés, mentés, jóváhagyás és visszajelzés. Nincs verzió-diff, citation-szerkesztés, bekezdés-újragenerálás vagy forrás melletti szerkesztési workflow.
- **Javaslat:**
  - **Verzió-diff** draft-verziók közt.
  - **Citation-beszúrás/szerkesztés:** forrásból idézet vagy `chunk_id` beillesztése kontrollált módon.
  - **Oldal-melletti forrás-szerkesztés:** forráskártya mellett draft bekezdés szerkesztése.
  - **Bekezdés újragenerálása** célzott forrásokkal és output-mode megőrzéssel.
  - **Jóváhagyás előtti checklist:** forrás, verify, disclaimer, eszkalációs állapot.
- **Backend:** részben létezik (draft verziók); bekezdés-újrageneráláshoz új endpoint kell.
- **Frontend:** `DraftEditor`, `DraftVersionDiff`, `CitationInsertMenu`, `ApprovalChecklist`.
- **Erőfeszítés:** M. **Kockázat:** alacsony-közepes.
- **Státusz 2026-06-09:** első implementáció elkészült: draft verzió-diff panel, citation beszúró menü, forrás-preview gomb, jóváhagyási checklist. Későbbi bővítés: célzott bekezdés-újragenerálás backend endpointtal és fejlettebb side-by-side diff.

#### J — ÁSZF-tudásböngésző

- **Javaslat:** böngészhető hierarchia-fa (`paragrafus_szam`) + kereszthivatkozási gráf (`cross_refs`); az ügyintéző közvetlenül navigál a forrásokban, §-ra keres, látja a hivatkozási hálót.
- **Backend:** új kis böngésző/keresés-végpont (`/aszf/tree`, `/aszf/section/{id}`, opcionálisan `/aszf/search`) a meglévő chunk-adatból.
- **Frontend:** új `screens/Knowledge.tsx` (+ nav), fa- és gráf-komponens.
- **Erőfeszítés:** M. **Kockázat:** alacsony.
- **Státusz 2026-06-09:** első implementáció elkészült: `/aszf/tree`, `/aszf/section/{chunk_id}`, `/aszf/search`, új Knowledge képernyő, nav elem, szakaszfa, keresési találatok és `cross_refs` megjelenítés. Későbbi bővítés: vizuális hivatkozási gráf és mélyebb §-szintű dokumentumhierarchia.

---

## 3. Prioritált ütemterv

### Fázis 1 — Backend már létezik, legjobb ROI

**A** forrás-provenance munkafelület -> **B** audit/compliance konzol -> **C** eval-dashboard továbbfejlesztés.

Ezek a meglévő, részben rejtett backend-erőt teszik használhatóvá, és közvetlenül a forrásoltságot, auditálhatóságot és minőségmérést javítják.

### Fázis 2 — Új backend vagy DB-séma is kell

**D** SSE-streaming -> **E** supervisor operációs konzol -> **F** Copilot session és handoff.

### Fázis 3 — Produktivitás / új felületek

**G** inbox produktivitás -> **H** command palette -> **I** draft power-szerkesztés -> **J** tudásböngésző.

### Függőségek

- A -> `agent_state.verify`, `retrieval`, `policy_map` típusok pontosítása (`frontend/src/lib/types.ts`).
- B -> `api.ts` bővítés audit events, completeness, traces endpointokra.
- C -> acceptance endpoint frontend bekötése.
- D -> backend streaming endpoint + szinkron fallback.
- E -> DB-séma bővítés (`cases.assignee`, `claimed_by`, opcionálisan SLA policy/breach mezők).
- F -> Copilot session perzisztencia vagy legalább explicit UI handoff állapot.
- G/E -> assignee és dedup backend mezők, ha a frontend-only mentett nézeteken túl megy.

---

## 4. Keresztmetszeti elvárások (minden tételre)

- **One tokenek / Tailwind `one-*`**; named exportok; `tsc --noEmit` + `npm run build` tiszta.
- **a11y:** `aria-*`, fókuszgyűrű, billentyű-elérhetőség, stabil méretű vezérlők.
- **RBAC + audit:** érzékeny műveletek szerepkör-kötöttek és naplózottak.
- **PII:** maszkolatlan PII csak unmask-RBAC után; a kimenő szövegből a `[Sn]` jelölők eltávolítva.
- **Offline-biztos** betöltés; soronkénti hibakezelés.
- **Contract:** új UI-mezőhöz backend response model vagy célzott contract teszt.
- **Teszt:** új komponenshez/viselkedéshez célzott teszt vagy legalább `tsc`/build-kapu.

---

## 5. Javasolt első lépés

**Fázis 1 / A — Forrásoltság & provenance-munkafelület.**

Ez hasznosítja közvetlenül a már meglévő RAG/verify adatokat (`retrieval_source`, `unresolved_refs`, `verify.claims`), kevés backendmunkával ad látható értéket, és az ügyintéző legkritikusabb kérdésére válaszol: melyik állítás pontosan milyen forrásból következik, és hol hiányzik a fedezet.
