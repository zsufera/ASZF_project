# UI-roadmap — funkcionális fejlesztési lehetőségek

> **Cél:** nagyobb, **funkcionalitásbeli** UI-fejlesztések specifikációja a React frontendhez (`frontend/`), a meglévő FastAPI backendre illesztve. Nem stílus/kozmetika — a use-case magját (auditálható, forrásolt, ember-kontrollált ügyintézői copilot) erősítő, működő funkciók.
> **Forma:** stratégiai roadmap, tételenként implementálható spec-vázlat. Minden tétel külön implementációs tervvé (`docs/superpowers/plans/`) bontható.
> **Kapcsolódó:** [`docs/archive/design-export/`](archive/design-export/) (archivált One arculat/tokenek), [`frontend/UX-DECISIONS.md`](../frontend/UX-DECISIONS.md), [`docs/rag-roadmap.md`](rag-roadmap.md), [`FEJLESZTESI_GUARDRAILS.md`](../FEJLESZTESI_GUARDRAILS.md) (§7 UI guardrailek).
> **Megjegyzés:** az „F) Tool-calling / élő ügyféladat" tétel szándékosan kimaradt (külön agentic-irány, lásd rag-roadmap E1 / agentic-javaslatok).

---

## 0. Jelenlegi állapot (kódra hivatkozva)

**Képernyők** (`frontend/src/screens/`): `Login`, `Inbox`, `CaseWorkstation`, `NewCase`, `Copilot`, `Postal`, `Evaluation` (~171 sor), `Supervisor` (~179 sor).
**Komponensek** (`frontend/src/components/`): `AppShell`, `IconNav`, `TopHeader`, `AgentTimeline` + `TimelineStep`, `RichSourceCard`, `InlineAnswer`, `DraftEditor`, `ProcessingIndicator`, `CaseBadgeRow`, `HistoryCard`, `CustomerCandidate`, `KpiCard`, `Modal`, `Toast`, `OfflineBanner`.
**API-réteg** (`frontend/src/lib/api.ts`): bekötve a copilot/ügy/draft/approve/feedback/history/customer-lookup/eval/supervisor/audit-cases/governance-purge.

### A legnagyobb funkcionális rés: kihasználatlan backend-erő
| Backend-képesség | Végpont | UI-állapot |
|---|---|---|
| Audit-esemény stream | `/audit/events` | **nincs bekötve** az api.ts-be |
| Audit-completeness ügyenként | `/audit/completeness/{id}` | **nincs bekötve** |
| Ügy-audit (iterációk) | `/audit/cases/{id}` | bekötve (`getAuditCase`), **de nincs képernyő** |
| Observability trace-ek | `/observability/traces` | **nincs bekötve** |
| Acceptance-kapu | `/acceptance/run` | **nincs bekötve** |
| Governance/retention purge | `/governance/purge` | bekötve, **nincs felület** |
| Újraindexelés | `/reindex` | **nincs bekötve** (a header gomb el lett távolítva) |
| Verify (LLM-judge) claim-szintű kimenet | `/verify` + `agent_state.verify` | a timeline mutatja a lépést, de a **claim-szintű** grounding nem jelenik meg |
| Retrieval-provenance | `agent_state.retrieval` (`retrieval_source`, `unresolved_refs`, score) | a forrás-kártyák megvannak, de a **provenance/score/closure** nem látszik |

---

## 1. Tervezési alapelvek
1. **Backend-elsőbbség hasznosítása:** ahol a végpont már létezik, az UI-érték magas és gyors. A 🥇 tier ilyen.
2. **A forrásoltság/audit a use-case magja** (guardrails §2, §7): minden nagyobb UI-fejlesztés ezt erősítse, ne hígítsa.
3. **HITL & RBAC:** az ügyfél-felé menő / érzékeny műveletek (unmask, approve, purge) szerepkör-kötöttek és auditáltak maradjanak.
4. **One arculat & tokenek:** archivált forrás `docs/archive/design-export/tokens.css` + `tailwind.tokens.js`, `one-*` osztályok; named exportok; `tsc --noEmit` + `npm run build` tiszta.
5. **a11y & órákig használat:** billentyű-vezérelhetőség, `aria-*`, fókuszgyűrű — az ügyintéző egész nap ezt nézi.
6. **Offline-biztos:** a `OfflineBanner` mintára minden új nézet kezelje a backend-hiányt.

---

## 2. Roadmap tételenként

### 🥇 Tier 1 — nagy érték, a backend MÁR létezik

#### A — Audit & compliance konzol  ⭐ compliance-kritikus
- **Gap:** szabályozott, auditálható copilot, de az audit/governance/trace végpontok nincsenek felületen.
- **Javaslat:**
  - **Ügy-szintű audit fül** a CaseWorkstationben: idővonal (ki/mikor/mit), **PII-hozzáférési napló** (unmask/approve), modell/prompt/`aszf_version`, döntési okok (eszkaláció, verify) — `/audit/cases/{id}` + `/audit/completeness/{id}`.
  - **Completeness-indikátor** ügyenként (a kötelező audit-mezők megléte).
  - **Globális audit-nézet** (új nav-pont, supervisor): esemény-kereső/szűrő — `/audit/events`.
  - **Governance/retention** panel (supervisor): purge **dry-run** előnézet — `/governance/purge`.
  - **Trace-viewer** (opcionális): `/observability/traces`.
- **Backend:** **létezik** (api.ts-be: `getAuditEvents`, `getAuditCompleteness`, `getTraces`).
- **Frontend:** új `screens/Audit.tsx` (+ nav), `CaseWorkstation` audit-fül, `components/AuditTimeline`, `PiiAccessLog`.
- **Erőfeszítés:** M-L · **Kockázat:** alacsony · **RBAC:** supervisor-only a globális/governance részekhez.

#### B — Forrásoltság & provenance-munkafelület  ⭐ a RAG/verify-munka láthatóvá tétele
- **Gap:** a retrieval-provenance és a verify claim-szintű kimenete nem jelenik meg; a válasz↔forrás kapcsolat csak az inline `[Sn]` chipekig megy.
- **Javaslat:**
  - **Claim-szintű groundedness-kiemelés:** a draft mondatai színezve (megalapozott/nem) a `agent_state.verify.claims` (LLM-judge) alapján; hover → a támasztó forrás.
  - **Forrás-provenance badge** a `RichSourceCard`-on: miért van itt — `szemantikus` / `referencia-closure` / `parent-context` / `auto-merged` (a `retrieval_source` mezőből) + relevancia-score.
  - **Be-nem-húzható hivatkozások panele:** a `retrieval.unresolved_refs` kiemelt megjelenítése („hivatkozott, de nem behúzható szakaszok") — a completeness-jel láthatóvá tétele a forrás-oldalon (a timeline-on már ott van).
  - **Hivatkozási-gráf mini-nézet** (opcionális, később): a `cross_refs` vizualizációja a forrás körül.
- **Backend:** **létezik** (a `verify`, `retrieval` már a `agent_state`-ben van; csak ki kell vezetni a típusokba/komponensekbe).
- **Frontend:** `lib/types.ts` (`VerifyClaim`, `unresolved_refs`, `retrieval_source`), `components/InlineAnswer` (claim-grounding mód), `components/RichSourceCard` (provenance badge), `screens/CaseWorkstation` (unresolved panel).
- **Erőfeszítés:** M · **Kockázat:** alacsony · **Megjegyzés:** a legközvetlenebb hatás a most elkészült RAG-rétegre.

#### C — Evaluation & minőség-dashboard
- **Gap:** az Evaluation képernyő vékony; az eval-harness ereje (baseline-diff, human-score, acceptance) nincs kihasználva.
- **Javaslat:**
  - **KPI-panel cél-küszöbökkel** (zöld/sárga/piros a `config/eval_targets.yaml` szerint): faithfulness, citation-support, coverage, escalation-appropriateness, p95 latencia, out-of-scope.
  - **Baseline-regresszió diff:** `/eval/baseline` — mely KPI romlott/javult az előző futáshoz képest.
  - **Bukó-eset drill-down:** egy gyenge eset megnyitása → mely forrás, miért nem megalapozott (a verify-judge alapján).
  - **Emberi spot-check:** 1–5 pontozás — `/eval/human-score`.
  - **Acceptance-gate státusz** (supervisor): `/acceptance/run`.
- **Backend:** **létezik** (eval/run/runs/baseline/human-score wired; `/acceptance/run` az api.ts-be).
- **Frontend:** `screens/Evaluation` kibővítés, `components/KpiCard` (küszöb-státusz), `EvalRegressionDiff`, `EvalCaseDrilldown`.
- **Erőfeszítés:** M · **Kockázat:** alacsony.

### 🥈 Tier 2 — nagy érték, némi új backend kell

#### D — Valódi agent-streaming (SSE)
- **Gap:** a `ProcessingIndicator` szimulált (a `/agent/run` egyetlen JSON, ~60s). Nincs valós lépés-visszajelzés.
- **Javaslat:** **SSE végpont** (`/agent/run/stream`) a LangGraph `astream_events`-szel → lépésenkénti node-completion események + a draft token-streamje; a frontend `EventSource`-szal fogadja. A `ProcessingIndicator` a **valós** lépéseket mutatja; a draft élőben épül.
- **Backend:** **ÚJ** (SSE endpoint + a graph streamelése; a node-ok már részleges state-et adnak vissza, ami eseményforrás).
- **Frontend:** `lib/api.ts` (EventSource), `ProcessingIndicator` (valós lépések), `Copilot`/`CaseWorkstation` (token-stream a drafton).
- **Erőfeszítés:** M-L · **Kockázat:** közepes (streaming/hibakezelés, fallback a szinkron útra).

#### E — Supervisor operációs konzol
- **Gap:** a Supervisor sor+statisztika; nincs valódi munkafolyamat.
- **Javaslat:** ügy **átvétel/kiosztás** (claim/assign), eszkaláció **jóváhagyás/felülbírálás**, **SLA-számláló + lejárat-riasztás**, bulk műveletek (lezárás/újranyitás), supervisor-döntés audit. Státusz-workflow `/cases/status`-szal.
- **Backend:** **részben** (státusz-workflow van; az **assignee/claim** mezők ÚJ DB-mezőt igényelnek).
- **Frontend:** `screens/Supervisor` kibővítés, `components/EscalationQueue`, `SlaCountdown`, bulk-akció sáv.
- **Erőfeszítés:** M-L · **Kockázat:** közepes (DB-séma bővítés).

### 🥉 Tier 3 — produktivitás / workflow

#### G — ÁSZF-tudásböngésző
- **Javaslat:** böngészhető **hierarchia-fa** (`paragrafus_szam`) + **kereszthivatkozási gráf** (a strukturált `cross_refs`-ből, amit a RAG-munka előállított); az ügyintéző közvetlenül navigál a forrásokban, §-ra keres, látja a hivatkozási hálót.
- **Backend:** **ÚJ** kis böngésző/keresés-végpont (`/aszf/tree`, `/aszf/section/{id}`) a meglévő chunk-adatból.
- **Frontend:** új `screens/Knowledge.tsx` (+ nav), fa- és gráf-komponens.
- **Erőfeszítés:** M · **Kockázat:** alacsony.

#### H — Agent-produktivitás
- **Javaslat:** **command palette** (Ctrl/Cmd-K) + billentyűparancsok (ügy megnyitás, feldolgozás, jóváhagyás), **mentett inbox-nézetek/szűrők**, **multi-csatorna dedup** (ugyanaz az ügyfél email/chat/telefon ügyei összevonva).
- **Backend:** részben (dedup logikához új lekérdezés); a többi frontend.
- **Frontend:** `components/CommandPalette`, `state` (mentett nézetek), `Inbox` szűrő-perzisztálás.
- **Erőfeszítés:** M · **Kockázat:** alacsony.

#### I — Draft power-szerkesztés
- **Javaslat:** **verzió-diff** a draft-verziók közt (`draft_versions`), **citation-beszúrás/szerkesztés**, **oldal-melletti forrás-szerkesztés**, „bekezdés újragenerálása" (cél-újragenerálás a synthesis-szel).
- **Backend:** részben (a verziók megvannak; a bekezdés-újragenerálás új kis végpont).
- **Frontend:** `components/DraftEditor` kibővítés, `DraftVersionDiff`.
- **Erőfeszítés:** M · **Kockázat:** alacsony.

---

## 3. Prioritált ütemterv

### Fázis 1 — Backend MÁR létezik (legjobb ROI, kevés/nulla backend-meló)
**B** provenance-munkafelület · **A** audit-konzol · **C** eval-dashboard.
> Ezek a meglévő (rejtett) backend-erőt teszik használhatóvá, és közvetlenül a use-case magját erősítik. **B a legközvetlenebb** (a most elkészült RAG/verify-réteget vezeti ki).

### Fázis 2 — Némi új backend
**D** SSE-streaming · **E** supervisor-konzol (DB-mező).

### Fázis 3 — Produktivitás / új felületek
**G** tudásböngésző · **H** produktivitás · **I** draft power-szerkesztés.

### Függőségek
- B → a `agent_state.verify`/`retrieval` típusok kivezetése (`lib/types.ts`).
- D (SSE) felülírja a `ProcessingIndicator` szimulált logikáját.
- E (assign/claim) → DB-séma bővítés (`cases.assignee`, `claimed_by`).
- A globális audit/governance + E + acceptance → **RBAC: supervisor-only**.

---

## 4. Keresztmetszeti elvárások (minden tételre)
- **One tokenek / Tailwind `one-*`**; named exportok; `tsc --noEmit` + `npm run build` tiszta.
- **a11y:** `aria-*`, fókuszgyűrű, billentyű-elérhetőség.
- **RBAC + audit:** érzékeny műveletek szerepkör-kötöttek és naplózottak (guardrails §11).
- **PII:** maszkolatlan PII csak unmask-RBAC után; a kimenő szövegből a `[Sn]` jelölők eltávolítva.
- **Offline-biztos** betöltés; soronkénti hibakezelés.
- **Teszt:** új komponenshez/viselkedéshez célzott teszt vagy `tsc`/build-kapu.

---

## 5. Javasolt első lépés
**Fázis 1 / B — Forrásoltság & provenance-munkafelület.** Tisztán frontend (a backend-adat már a `agent_state`-ben van), a legközvetlenebbül hasznosítja a most elkészült RAG-réteget (provenance, closure, unresolved, verify-judge), és a use-case magját (auditálható forrásoltság) erősíti. Mérhető: az ügyintéző a draft minden állításához egy kattintással lássa a támasztó forrást és annak provenance-át.
