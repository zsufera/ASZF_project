# ÁSZF Q&A Agent — Fejlesztési guardrailek

> Ezt a dokumentumot a fejlesztés során folyamatos iránytűként kell használni. Célja, hogy a POC ne sodródjon el a hosszú távú üzleti céloktól: forrásolt, auditálható, ember által kontrollált ügyfélszolgálati copilot épüljön, nem autonóm ügyfélkommunikációs rendszer.

## 1. Termékcél

- A rendszer **belső ügyintézői copilot**, nem ügyféllel közvetlenül kommunikáló agent.
- Elsődleges érték: ÁSZF-részek gyors megtalálása, pontos forráshivatkozás, válaszlevél-draft és eszkalációs döntéstámogatás.
- Minden fejlesztési döntésnél ezt kell kérdezni: **javítja-e az ÜI döntési minőségét, gyorsaságát vagy auditálhatóságát?**

## 2. Nem alkuképes alapelvek

- **Human-in-the-loop**: ügyfél felé menő tartalom csak emberi jóváhagyás után, POC-ban csak mock küldéssel.
- **Forrás-kötelezettség**: tartalmi állítás csak visszakeresett ÁSZF / melléklet / egyéb feltétel alapján.
- **Nincs hallucinált jogi állítás**: ha nincs forrásfedezet, a rendszer jelezze a hiányt és javasoljon eszkalációt.
- **PII-minimalizálás**: felhős LLM felé csak maszkolt szöveg mehet.
- **Eszkaláció, nem „emelés”**: az eszkalációs fogalmat következetesen így kell nevezni; a `díjemelés` kategória külön üzleti fogalom.
- **Postai PDF/OCR külön kapu**: OCR-eredmény csak ÜI-korrekciós előnézet után léphet a normál email-flow-ba.

## 3. Scope-fegyelem

### Benne van a POC-ban
- ÁSZF ingest lokális PDF fallbackkel.
- §/szakasz-szintű chunkolás metaadatokkal.
- Forrásolt retrieval és válasz-draft.
- Email, postai PDF, chat/telefon copilot bemenet.
- Előzmény-kontextus azonos email cím alapján.
- Mock ügyféltörzs-jelöltek UI-helye.
- SQLite audit, draft-verzió, státuszkezelés.

### Tudatosan későbbi fázis
- Valós CRM / ügyféltörzs / email-küldés integráció.
- Automatikus deduplikáció többcsatornás ügyekre.
- Email-csatolmányok teljes OCR feldolgozása.
- Többszintű supervisor/jogi approval workflow.
- Production-grade titkosítás, retention, append-only audit.

Ha egy feladat a későbbi fázisba tartozik, csak interfészt vagy mockot készítsünk hozzá, ne teljes éles integrációt.

## 4. Architektúra guardrailek

- **LangGraph** az agent-lépésekhez: minden node kimenete legyen állapotba írható és UI-on megjeleníthető.
- **FastAPI** legyen az egyértelmű backend határ; a UI ne hívjon közvetlen ingest/agent belső függvényeket.
- **Streamlit** legyen vékony UI-réteg: workflow, megjelenítés, emberi jóváhagyás; üzleti logika backendben.
- **SQLite** a POC perzisztencia; ne vezessünk be Postgres/Redis komplexitást, amíg nincs tényleges szükség.
- **Qdrant** a vektoros/hibrid keresés célrendszere; lokális fallback keresés csak fejlesztési és smoke célra.
- **Adapterek** külső rendszerekhez: `CaseStore`, email-adapter, `CustomerDirectory`. Éles integráció helyett mock az első körben.

## 5. Ingest guardrailek

- Minden chunk legyen visszavezethető: `doc_id`, `source_file`, `szolgaltato`, `dok_tipus`, `dok_cim`, `oldalszam`, `paragrafus_szam`.
- A négy szolgáltató dokumentumai ne keveredjenek; retrievalnél szolgáltató-szűrés legyen támogatott.
- A táblázatok szerkezetét lehetőség szerint őrizni kell, mert díj/díjcsomag témában üzletkritikusak.
- Kereszthivatkozásokat (`cross_refs`) gyűjteni kell, később retrievalkor kapcsolódó §-ként behúzhatók.
- A manifest legyen reprodukálható és hash-alapú deduplikációt használjon.

## 6. Agent guardrailek

- A node-sorrend: nyelv/típus → maszkolás → osztályozás → prioritás → szabályzat-térkép → eszkaláció → sablon/intézkedés → draft → verify → unmask.
- A maszkolás után minden LLM-hívás maszkolt tartalommal dolgozzon.
- Az eszkalációs döntés legyen magyarázható: okok listája, trigger, konfidencia vagy SLA.
- Az agent ne döntsön pénzügyi/jogi következményű intézkedésről automatikusan.
- A draft szerkeszthető legyen, és a forráshivatkozásokat az ÜI módosíthassa.

## 7. UI guardrailek

- Az ÜI mindig lássa:
  - agent-idővonalat,
  - forrásokat szó szerinti idézettel,
  - közérthető magyarázatot,
  - konfidenciát,
  - eszkaláció okát,
  - SLA státuszt.
- A forráspanel és a draft soha ne váljon szét logikailag: a draftban szereplő állítások legyenek visszakereshetők a források között.
- Az ügyféltörzs-jelöltek panel csak jelöltlistát ad; az ügyfél-azonosítás végső döntése az ÜI-é.
- Postai importnál az OCR bizonytalan részei legyenek láthatók és javíthatók.

## 8. Kódírási elvárások

- **Kis, célzott változtatások**: egy commitnyi/logikai egység egy jól körülhatárolt viselkedést változtasson.
- **Szerződés-specek tisztelete**: API, adatmodell, állapot-séma és konfig mezőnevek a `ASZF_QnA_Agent_contract_spec.md` szerint maradjanak.
- **Típusosság**: új Python kódnál használj típusannotációkat a publikus függvényeken, request/response objektumokon és állapot-sémákon.
- **I/O határok szétválasztása**: fájl/DB/API hívás legyen vékony adapterben; a tiszta üzleti logika legyen külön, tesztelhető függvényben.
- **Nincs rejtett globális állapot**: runtime konfig a `config/settings.py`-ból, paraméterezhető függvényekkel. Tesztekben legyen könnyen felülírható.
- **Determinista fallback**: LLM/Qdrant/OCR nélküli fejlesztéshez legyen determinisztikus stub vagy fallback, de egyértelműen jelölve.
- **Hibakezelés**: külső I/O hibát ne nyeljünk el; adjunk érthető hibát és audit/smoke diagnosztikát.
- **PII-biztonság alapértelmezésben**: új log, print, exception és audit payload ne tartalmazzon maszkolatlan PII-t.
- **Terminológia kódban is**: eszkalációs mezők angolul `escalation`, magyar UI/spec szövegben `eszkaláció`; ne vezess be `emeles` mezőt.
- **Dokumentáció frissítése**: ha változik futtatási mód, CLI, endpoint vagy config, frissítsd a README-t vagy a releváns specet ugyanabban a lépésben.

## 9. Tesztelési guardrailek

- Új viselkedéshez legyen legalább egy célzott teszt vagy smoke ellenőrzés.
- Új üzleti logikához először írj tesztet vagy rögzített smoke esetet; implementáció csak utána.
- Tesztpiramis:
  - unit: tiszta logika (`manifest`, chunkolás, retrieval mapping, eszkalációs szabályok, PII-maszkolás),
  - integráció: API endpoint + fájl/SQLite/Qdrant adapter,
  - smoke: ingest → retrieve → forrásos találat, illetve inbox → draft flow.
- PII-maszkolás kritikus: tesztelje, hogy maszkolatlan PII nem kerül LLM-promptba.
- Retrieval esetén minimális elvárás: kérdés → legalább egy forrásos chunk `chunk_id` + idézet + dokumentumtípus mezővel.
- Agent-kimeneteknél strukturális asserteket használjunk: van citation, van eszkaláció trigger esetén, automata módban van disclaimer.
- Snapshot-szerű teljes LLM-szövegteszteket kerüljük, mert törékenyek.
- LLM-es viselkedést ne szó szerinti szöveggel tesztelj; mezők, források, flag-ek, schema-validitás legyen az assert.
- OCR/parse teszteknél legyen kis fixture PDF vagy minimális fixture szöveg, hogy ne kelljen teljes ÁSZF-korpuszt futtatni minden teszthez.
- Qdrant/infrastruktúra nélküli unit teszteknek menniük kell lokális fallbackkel; Qdrant teszt külön integrációs jelölést kapjon.
- Minden regresszióhoz adj tesztet, ami a hibát reprodukálja.
- Ha a shell/tesztfuttatás nem ad megbízható exit státuszt, nem szabad sikeres tesztként hivatkozni rá.

## 10. Minőségi kapuk

Egy fejlesztési lépés akkor tekinthető késznek, ha:

- Lint/diagnosztika nem jelez új hibát az érintett fájlokon.
- A releváns unit/smoke teszt futtatható vagy a futtatási akadály dokumentált.
- Új endpointnál legyen request/response séma és legalább egy pozitív smoke teszt vagy példa.
- Új DB mező/tábla esetén frissüljön a contract spec vagy a migrációs megjegyzés.
- Új agent-node vagy prompt-output esetén frissüljön az állapot-séma és a prompt-katalógus.
- A README vagy kapcsolódó spec frissült, ha változott a futtatás vagy szerződés.
- Az auditálhatóság nem romlott: modell/prompt/forrásverzió vagy döntési ok továbbra is rögzíthető.
- A változtatás nem vezet be maszkolatlan PII-egress kockázatot.
- A változtatás visszagörgethető legyen adatvesztés vagy destruktív mellékhatás nélkül.

## 11. Kód review ellenőrzőlista

Minden nagyobb változtatás előtt/után gyorsan ellenőrizd:

- Megmaradt a human-in-the-loop és mock küldési alapelv?
- Minden tartalmi válasz forrásolható `chunk_id` alapján?
- Nem került maszkolatlan PII logba, trace-be, promptba vagy teszt fixture-be?
- Az eszkalációs döntés okai auditálhatók?
- Nem keveredhetnek a szolgáltatók dokumentumai retrieval közben?
- Az új kód tesztelhető külső szolgáltatás nélkül?
- A README/spec/contract változott, ha a külső viselkedés változott?

## 12. Terminológiai konzisztencia

- Használandó: **eszkaláció**, **eszkalált ügy**, **eszkalációs trigger**, **eszkalációs döntés**.
- Ne használd eszkalációs értelemben: „emelés”.
- Kivétel: **díjemelés** üzleti kategória, valamint **kiemelés/kiemelt** UI vagy kockázati értelemben.
- Dokumentumtípusok: `ÁSZF`, `melléklet`, `Egyéb felhasználási feltételek`.
- Csatornák: `email`, `chat`, `telefon`, `postai`.

## 13. Fejlesztési fókusz-sorrend

1. Stabil ÁSZF ingest: manifest → parse → chunk → index → retrieve.
2. Forrásolt RAG válasz-szintézis.
3. Maszkolás + audit + eszkalációs döntés.
4. Minimál UI végpontig: inbox → ügy nézet → draft → jóváhagyás.
5. Evaluation harness és KPI-k.
6. Kényelmi funkciók, integrációs mockok bővítése.

Ha két feladat versenyez, azt válasszuk előbb, amelyik a forrásoltságot, auditálhatóságot vagy PII-biztonságot javítja.

## 14. Módosítási szabály

Ha egy új üzleti igény érkezik:

1. Döntsd el, POC-scope vagy roadmap.
2. Írd be a megfelelő specbe.
3. Add hozzá a „miért” indoklást.
4. Ellenőrizd a terminológiai és architekturális konzisztenciát.
5. Csak ezután implementáld.

