# Nem UI fókuszú fejlesztési roadmap

> **Cél:** azoknak a fejlesztési irányoknak a rögzítése, amelyek nem elsődlegesen UI-használhatósági tételek, de a rendszer agentic érettségét, üzleti használhatóságát, integrálhatóságát, auditálhatóságát vagy üzemeltethetőségét javítják.
> **Kapcsolódó:** [`docs/ui-roadmap.md`](ui-roadmap.md), [`docs/agentic_refactor_roadmap.md`](agentic_refactor_roadmap.md), [`docs/codebase_simplification_roadmap.md`](codebase_simplification_roadmap.md), [`FEJLESZTESI_GUARDRAILS.md`](../FEJLESZTESI_GUARDRAILS.md).
> **Frissítve:** 2026-06-09.

---

## 1. Agentic érettség és kontrollált tool-használat

### A — Copilot tool registry bővítése

- **Jelenlegi állapot:** a Copilot orchestrator kontrollált subagent/tool készletet használ (`classify`, `knowledge_search`, `customer_context`, `escalation_advice`, `draft_reply`, `verify_grounding`).
- **Javaslat:** új, továbbra is belső és ember-kontrollált toolok:
  - `audit_check`: audit completeness és legfontosabb hiányok lekérése.
  - `prepare_escalation_package`: supervisor átadási csomag készítése indokokkal, forrásokkal, verify státusszal.
  - `status_transition_advice`: megengedett státuszlépések és kockázatok visszaadása, tényleges váltás nélkül.
  - `rewrite_draft_section`: egy bekezdés célzott újraírása megadott forrásokkal.
  - `source_gap_analysis`: hiányzó kötelező hivatkozások és unresolved refs összefoglalása.
- **Kontroll:** egyik tool se küldjön ügyfélnek tartalmat és ne változtasson állapotot explicit emberi jóváhagyás nélkül.

### B — Verify utáni repair/escalation ciklus

- **Jelenlegi állapot:** a LangGraph lineáris: draft -> verify -> prepare_unmask. A verify eredmény blokkolhat jóváhagyást, de nincs automatikus javítási kísérlet.
- **Javaslat:** ha `verify.ungrounded_count > 0`, `missing_mandatory` van, vagy `generation_mode == "insufficient"`, az agent:
  - próbáljon célzott retrievalt a hiányzó állításra,
  - javítsa vagy törölje a nem alátámasztott bekezdést,
  - ha nincs fedezet, állítsa `insufficient/escalation` állapotba.
- **Korlát:** maximum 1-2 repair iteráció, auditált döntési okokkal, hogy ne legyen végtelen LLM ciklus.

### C — Copilot session perzisztencia

- **Jelenlegi állapot:** a Copilot chat azonnali válaszra és session-szintű ügyhivatkozásra épül, a session nem teljes értékű perzisztált üzleti entitás.
- **Javaslat:** perzisztált `copilot_sessions` és `copilot_turns` tárolás:
  - masked user/assistant turnök,
  - tool-call observations,
  - források,
  - létrehozott case kapcsolat,
  - audit meta (modell, prompt, ÁSZF-verzió).
- **Üzleti érték:** visszakereshető telefon/chat segítség, ügy-handoff audit, kevesebb elvesző kontextus.

---

## 2. Üzleti workflow és döntési kontrollok

### D — Supervisor claim/assign és SLA modell

- **Jelenlegi állapot:** van státusz workflow és supervisor queue, de nincs assignee/claim mező, nincs kategória/csatorna szerinti SLA policy és nincs SLA breach külön esemény.
- **Javaslat:**
  - DB-séma bővítés: `cases.assignee_user_id`, `claimed_by_user_id`, `claimed_at`, `sla_due_at`, `sla_breached_at`.
  - Endpointok: claim, release, assign, bulk assign, SLA breach scan.
  - Audit események: claim, assign, release, SLA breach, supervisor override.
- **Kontroll:** státuszváltás továbbra is `backend.workflow` validációval történjen.

### E — Többszintű approval előkészítése

- **Jelenlegi állapot:** v1 egyszintű jóváhagyás, RBAC unmask/approve kontrollal.
- **Javaslat:** kockázatalapú approval policy:
  - alacsony kockázat: ügyintéző jóváhagyás,
  - közepes: supervisor jóváhagyás,
  - magas/jogi: jogi queue vagy manuális átadás.
- **Trigger források:** eszkalációs okok, alacsony konfidencia, verify warning, egyedi szerződés gyanú, vitatott összeg, hatósági/jogi kulcsszavak.
- **POC-kompatibilis első lépés:** policy döntés és audit mezők mock jogi szerepkör nélkül.

### F — Valódi integrációs adapter contractok

- **Jelenlegi állapot:** van minimális `CaseStore` protocol és mock ügyféltörzs/email adapter irány.
- **Javaslat:** bővített adapter contractok:
  - `TicketingAdapter`: create/update/get/status/assign.
  - `OutboundMessageAdapter`: draft handoff, mock send, később email send.
  - `CustomerDirectory`: customer lookup, service provider, subscription ids.
  - `DocumentSourceAdapter`: ÁSZF verziók, letöltés, hash, hatályosság.
- **Kontroll:** minden adapter masked-by-default payloadot kapjon, PII-egress külön engedélyezéssel.

---

## 3. Tudásfrissítés és dokumentum-governance

### G — Tudásfrissítési workflow

- **Jelenlegi állapot:** van `/reindex`, ingest pipeline és manifest, de nincs jóváhagyási folyamat az új dokumentumverziókra.
- **Javaslat:**
  - dokumentumváltozás észlelése hash/manifest alapján,
  - ÁSZF-verzió diff riport,
  - mandatory refs és disclaimer változások jelzése,
  - jogi/supervisor jóváhagyási kapu,
  - jóváhagyott reindex audit eseménnyel.
- **Első lépés:** CLI/API szintű `reindex_plan` riport, UI nélkül.

### H — Mandatory-ref és policy paraméterezés governance

- **Jelenlegi állapot:** a `config/mandatory_refs.yaml`, `config/policies.yaml`, `config/disclaimer.yaml` generált/konfigurált fájlokként működnek.
- **Javaslat:** policy változás audit:
  - ki módosította,
  - milyen ÁSZF verzióból következik,
  - milyen kategóriát érint,
  - milyen eval/golden case futott utána.
- **Kontroll:** policy változás csak acceptance gate után legyen élesíthető.

---

## 4. Evaluation, acceptance és regressziókontroll

### I — Golden case regressziós készlet bővítése

- **Javaslat:** gyors, determinisztikus golden suite a fő üzleti utakra:
  - számlázási panasz,
  - hibabejelentés,
  - szerződésfelmondás,
  - ismétlődő panasz stabil sender key alapján,
  - azonos mask token külön feladókkal,
  - LLM outage template fallbackkel,
  - nincs forrás -> insufficient,
  - query rewrite hiba -> rule fallback.
- **Cél:** agent/RAG változtatás előtt gyorsan látszódjon, sérül-e a fő üzleti viselkedés.

### J — Acceptance gate üzleti kapuvá alakítása

- **Jelenlegi állapot:** van acceptance service és endpoint, de a fejlesztési/üzleti döntésekben még nincs központi szerepe.
- **Javaslat:** acceptance eredmény tartalmazza:
  - eval KPI célok,
  - audit completeness,
  - demo forgatókönyv státusz,
  - kritikus guardrail ellenőrzések (PII, source citation, verify warning),
  - változás előtti/utáni diff.
- **Kontroll:** production/pilot jellegű változás csak acceptance pass vagy dokumentált waiver mellett.

### K — Feedback loop strukturálása

- **Jelenlegi állapot:** UI feedback van (`jó/rossz`, `rossz forrás`), de nincs visszacsatolási pipeline.
- **Javaslat:** feedback adatmodell:
  - kategória,
  - hibafajta (rossz forrás, rossz kategória, rossz hangnem, hiányos válasz, eszkalációs hiba),
  - érintett source/citation,
  - javítás státusza.
- **Cél:** emberi értékelésből fejlesztési backlog és regressziós eset legyen.

---

## 5. Architektúra és szerződésstabilitás

### L — API contract formalizálása

- **Jelenlegi állapot:** TypeScript típusok és Pydantic response-ok kézzel vannak összehangban tartva, contract tesztekkel részben védve.
- **Javaslat:**
  - Pydantic response modellek a fő endpointokra,
  - OpenAPI alapú TypeScript típusgenerálás vagy erősebb contract tesztek,
  - kiemelt payloadok: `GET /cases/{id}`, `POST /agent/run`, `POST /copilot/chat`, `GET /audit/cases/{id}`, `POST /eval/run`.
- **Cél:** frontend regressziók hamarabb bukjanak buildben vagy tesztben.

### M — Repository réteg SQLite hozzáféréshez

- **Jelenlegi állapot:** több service közvetlenül nyit SQLite kapcsolatot.
- **Javaslat:** fokozatos repository bontás:
  - `case_repository`,
  - `draft_repository`,
  - `audit_repository`,
  - `copilot_session_repository`,
  - migration/backfill helper.
- **Cél:** könnyebb DB-séma bővítés (assignee, SLA, copilot sessions), stabilabb tesztek.

### N — Runtime/generált adatok review-zajának csökkentése

- **Javaslat:** trace-ek, derived reportok és timestamp-only változások kezelése külön artifactként vagy ignore policyval.
- **Cél:** PR review során a kódváltozás ne keveredjen runtime adatokkal.

---

## 6. Javasolt sorrend

1. Golden case regressziós készlet bővítése.
2. Verify utáni repair/escalation ciklus tervezése és contract tesztjei.
3. Supervisor claim/assign + SLA DB-séma előkészítése.
4. Copilot session perzisztencia.
5. API contract formalizálása a fő payloadokra.
6. Tudásfrissítési workflow első, UI nélküli riportja.
7. Adapter contractok bővítése ticketing/outbound/customer/document irányban.
8. Acceptance gate üzleti kapuvá erősítése.
9. Repository réteg bevezetése a következő DB-séma bővítés előtt.
10. Runtime/generált adatok review policy rendezése.

---

## 7. Nem cél ebben a roadmapben

- UI komponensek, képernyők és felületi ergonómia részletes tervei: ezek a [`docs/ui-roadmap.md`](ui-roadmap.md) részei.
- Autonóm ügyfélkommunikáció vagy felügyelet nélküli kiküldés: továbbra is tiltott a guardrailek szerint.
- Éles CRM/email integráció teljes implementációja POC-scope-ban: csak adapter contract és mock/controlled handoff.
