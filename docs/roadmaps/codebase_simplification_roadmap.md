# Teljes kódbázis egyszerűsítési és átláthatósági roadmap

## Cél

Ez a dokumentum az agentic/RAG rétegen kívüli egyszerűsítési lehetőségeket foglalja össze. A cél a repo áttekinthetőségének növelése, a review-zaj csökkentése, a régi és új UI-rétegek szétválasztása, valamint a backend/frontend szerződések stabilizálása.

## Fő egyszerűsítési irányok

### 1. Legacy Streamlit UI leválasztása vagy archiválása

A repo-ban jelenleg egyszerre él a React frontend és a régi `legacy/ui/` Streamlit app. A README szerint a React frontend az aktív UI, a legacy Streamlit kód, tesztek, dependencyk és dokumentációk pedig csak referenciaként maradhatnak.

Javasolt opciók:

- `legacy/ui/` megtartása elkülönített referenciafelületként.
- Streamlit tesztek külön legacy tesztprofilba mozgatása.
- Streamlit dependency külön `requirements-legacy.txt` fájlba.
- Ha már nincs üzleti szükség rá, a Streamlit UI teljes eltávolítása.

Elvárt eredmény: egyértelmű, hogy a React frontend az aktív UI, a legacy felület pedig nem befolyásolja a normál fejlesztést és CI-t.

### 2. Dokumentációk aktív és archív szétválasztása

Több dokumentum még Streamlit-alapú célállapotot ír le, miközben a tényleges termékirány React. Ez félrevezető lehet új fejlesztésnél vagy review során.

Javasolt struktúra:

- aktív dokumentáció:
  - `README.md`
  - aktuális API contract
  - aktuális architektúra
  - `docs/roadmaps/agentic_refactor_roadmap.md`
  - ez a roadmap
- archív dokumentáció:
  - régi Streamlit specifikációk
  - régi design exportok
  - korábbi implementációs planek

Javasolt mappa: `docs/archive/`

Elvárt eredmény: az aktív dokumentáció nem keveredik régi POC/legacy irányokkal.

### 3. Runtime és generated fájlok kiszorítása a review-ból

A `data/traces/*.jsonl`, derived reportok, timestamp-only config változások és diagnosztikai script-ek gyakran jelennek meg dirty state-ként. Ez megnehezíti annak eldöntését, hogy mi valódi kódváltozás.

Javaslat:

- runtime trace fájlok gitignore alá vagy artifact könyvtárba kerüljenek.
- generated/derived data változások külön commit-policy szerint kerüljenek be.
- timestamp-only config diffek ne keveredjenek kód PR-ba.
- `_diag_*.py` script-ek törlendők vagy `scripts/diagnostics/` alá kerüljenek dokumentáltan.

Elvárt eredmény: tisztább git diff, gyorsabb review, kisebb esély véletlen runtime adat commitolására.

### 4. Backend endpoint, service és repository réteg szétválasztása

A `backend/main.py` és `backend/case_service.py` sok felelősséget visz egyszerre: API route-ok, DB műveletek, workflow, audit, case állapot, draft verziózás, history.

Javasolt bontás:

- `backend/api/cases.py` - case route-ok
- `backend/api/history.py` - history route-ok
- `backend/api/agent.py` - agent route-ok
- `backend/repositories/case_repository.py` - SQLite case műveletek
- `backend/repositories/draft_repository.py` - draft verziók
- `backend/services/case_workflow_service.py` - feldolgozás és státuszváltás
- `backend/services/draft_service.py` - draft mentés, jóváhagyás
- `backend/services/history_service.py` - előzménykezelés

Elvárt eredmény: a FastAPI réteg vékony, az üzleti logika és DB-hozzáférés tesztelhetőbb és olvashatóbb.

### 5. Duplikált draft logika tisztítása

Még él a régi `build_draft()` út és az újabb `synthesize_answer()` vonal. Ez átmeneti állapotként érthető, de hosszabb távon regressziók forrása lehet.

Javaslat:

- `build_draft_template()` maradjon determinisztikus fallback builder.
- `build_draft()` legyen explicit deprecated wrapper vagy kerüljön ki.
- Az aktív agent/case/eval útvonalak egyértelműen `synthesize_answer()`-t használjanak.
- A tesztek külön fedjék:
  - LLM synthesis
  - template fallback
  - insufficient no-source eset

Elvárt eredmény: egy fő draft generálási út marad, kevesebb eltérő fallback viselkedéssel.

### 6. Frontend/backend API contract formalizálása

A frontend TypeScript típusok és a backend payloadok kézzel vannak összhangban tartva. Ez már több hibát okozott, például új mezők vagy generation mode-ok esetében.

Opciók:

- OpenAPI schema alapján TypeScript típusgenerálás.
- Pydantic response modellek minden fő endpointon.
- Contract tesztek a fő payload mezőkre.

Kiemelt endpointok:

- `GET /cases/{id}`
- `GET /history`
- `POST /agent/run`
- `POST /cases/process`
- `POST /cases/approve`

Elvárt eredmény: frontend build vagy contract teszt hamarabb jelzi a backend payload regressziókat.

### 7. Frontend komponens-struktúra tisztítása

A React frontend aktív UI, de néhány képernyő túl sok felelősséget hordoz. Különösen a `CaseWorkstation.tsx` tartalmaz adatbetöltést, állapotkezelést, layoutot, draft műveleteket, historyt, timeline-t és forrásmegjelenítést.

Javasolt komponensek:

- `CaseHeader`
- `CaseSourcesPanel`
- `CaseHistoryPanel`
- `CaseCustomerPanel`
- `CaseDraftPanel`
- `CaseTimelinePanel`
- `CaseInboundMessage`

Javasolt hook:

- `useCaseData(caseId)`
- `useCaseActions(caseId)`

Elvárt eredmény: kisebb komponensek, könnyebb UI módosítás, célzottabb tesztelhetőség.

### 8. Tesztstruktúra profilozása

A `tests/` alatt keverednek unit, API contract, integration, frontend string-contract és legacy Streamlit tesztek. Ez nehezíti a célzott futtatást.

Javasolt struktúra:

- `tests/unit/`
- `tests/api_contract/`
- `tests/integration/`
- `tests/frontend_contract/`
- `tests/legacy_streamlit/`

Javasolt marker:

- `pytest -m "not legacy"`
- `pytest -m api_contract`
- `pytest -m integration`

Elvárt eredmény: gyorsabb lokális futtatás, tisztább CI pipeline, legacy tesztek kontrollált kezelése.

### 9. SQLite hozzáférés központosítása

Több backend modul közvetlenül nyit SQLite kapcsolatot. Ez kicsiben működik, de migrációknál, backfilleknél és teszteknél törékeny.

Javaslat:

- repository réteg minden DB művelethez
- közös row mapping
- explicit migration/backfill modul
- tesztekben egységes DB fixture

Elvárt eredmény: kevesebb szétszórt SQL, könnyebb schema változtatás, stabilabb teszt setup.

### 10. Konfigurációs réteg egyszerűsítése

A `.env`, `config/*.yaml`, settings objektum, derived metadata és runtime állapot több helyen találkozik.

Javasolt bontás:

- runtime config: provider, model, DB path, Qdrant path
- policy config: compliance szabályok, mandatory refs
- generated config: derived reports, manifestek
- UI config: frontend env és build-time config

Javasolt kontroll:

- induláskori config validáció
- config diffek review policy szerint
- generated config külön artifact kezelés

Elvárt eredmény: kevesebb környezeti meglepetés, könnyebb lokális és production futtatás.

## Gyors nyereségek

1. `_diag_*.py` fájlok rendezése vagy törlése.
2. `.pytest_cache/`, `frontend/.vite/`, trace fájlok ignore policy ellenőrzése.
3. Streamlit dokumentációk `docs/archive/` alá mozgatása.
4. `backend/main.py` route-ok router modulokra bontása.
5. `CaseWorkstation.tsx` első komponensbontása.
6. `build_draft` használatok auditálása.
7. `requirements.txt` és legacy dependencyk szétválasztása.

## Javasolt megvalósítási sorrend

1. Runtime/generated/diagnosztikai fájlok rendbetétele.
2. Legacy Streamlit döntés: megtartás külön legacy profilban vagy eltávolítás.
3. Dokumentációk aktív/archív szétválasztása.
4. Backend route/service/repository bontás első szelete.
5. Frontend `CaseWorkstation` komponensbontás.
6. API contract erősítése.
7. Régi draft/build_draft út tisztítása.
8. Tesztstruktúra marker/profil bevezetése.
9. SQLite repository és migration/backfill réteg kialakítása.
10. Konfigurációs réteg validálása és szétválasztása.

## Kockázatok és kontrollok

- Legacy Streamlit eltávolítása előtt legyen döntés arról, hogy kell-e még referenciafelületként.
- Minden backend bontás előtt legyen API contract teszt.
- Repository réteg bevezetésekor kerülni kell a párhuzamos régi/új SQL utak hosszú együttélését.
- Frontend komponensbontás ne változtasson viselkedést első körben.
- Generated/runtime fájlok ignore-olása előtt ellenőrizni kell, hogy nincs-e valóban szükséges fixture köztük.
- Minden lépés legyen kis PR-kompatibilis egység, külön verifikációval.
