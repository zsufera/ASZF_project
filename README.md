# ASZF Q&A Agent (POC)

POC-level belső copilot telekom ügyfélszolgálathoz:
- ÁSZF-alapú forráshivatkozás
- válaszlevél-javaslat
- eszkalációs döntéstámogatás
- auditálható, human-in-the-loop működés

Fejlesztés közben kötelező iránytű: [FEJLESZTESI_GUARDRAILS.md](FEJLESZTESI_GUARDRAILS.md).

## Gyors indulás

1. Python környezet és csomagok:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. Környezeti változók:
   - másold: `.env.example` -> `.env`
3. Infrastruktúra:
   - `docker compose up -d`
4. Adatbázis inicializálás:
   - `python -m backend.db`
5. Backend indítás:
   - `uvicorn backend.main:app --reload`

## ÁSZF ingest első lépései

Másold a PDF-eket a `data/raw_pdfs/` mappába (POC elsődleges út).

1. Manifest generálás:
   - `python -m preprocessing.manifest`
   - kimenet: `data/ingest_manifest.json`
2. PDF parse + hierarchikus chunkolás:
   - `python -m preprocessing.parse`
   - kimenetek:
     - `data/processed/parsed_pages.jsonl`
     - `data/processed/chunks.jsonl`
3. Indexelés:
   - `python -m preprocessing.index --skip-qdrant` (lokális sparse fallback)
   - `python -m preprocessing.index` (Qdrant, ha fut a compose)
4. Dok-paraméterezés (Fázis 1b):
   - `python -m preprocessing.derive_params`
   - kimenetek: `config/policies.yaml`, `config/mandatory_refs.yaml`, `config/disclaimer.yaml`, `data/derived/derive_report.json`
5. Minta-emailek:
   - `python -m preprocessing.gen_emails`
   - kimenet: `data/sample_emails/`
6. Smoke ellenőrzés:
   - `python -m preprocessing.smoke_retrieve "számlázási kifogás" --service-provider ONE`
   - `python -m preprocessing.smoke_ingest --query "számlázási kifogás" --service-provider ONE`

Opcionális letöltő: `python -m preprocessing.download` (WAF esetén nem megbízható).

Ha nincs PDF a `data/raw_pdfs/` alatt, a manifest üres dokumentumlistával jön létre.
A `/retrieve` endpoint a `data/processed/chunks.jsonl` alapján lokális fallback keresést ad, így Qdrant nélkül is tesztelhető a forráshivatkozásos találat.

## Backend flow (Fázis 2)

Indítás: `uvicorn backend.main:app --reload`

Vertikális sorrend:

1. `POST /mask` -> visszafordítható PII-maszkolás (SQLite token-térkép)
2. `POST /classify` -> kategória + konfidencia + ismétlődés-jelzés
3. `GET /history?address=` -> azonos feladó előzményei (SQLite)
4. `GET /customer-lookup?address=` -> mock ügyféltörzs-jelöltek
5. `POST /retrieve` -> hibrid (sparse+dense) retrieval, cross-ref bővítés, opcionális Qdrant
6. `POST /policy-map` -> szabályzat-térkép + kötelező hivatkozások
7. `backend.escalation.decide_escalation()` -> eszkalációs helper
8. `POST /draft` -> válaszjavaslat citationökkel
9. `POST /verify` -> groundedness ellenőrzés
10. `POST /unmask` -> draft visszafejtés jóváhagyás előtt
11. `POST /ocr` -> postai PDF szövegkinyerés + maszkolás
12. `POST /reindex` -> manifest + parse + index + derive_params
13. `POST /eval/run` -> minta-email alapú retrieval/osztályozás metrikák

Minden válasz tartalmazza: `request_id`, `model_profile`, `prompt_version`, `aszf_version`.

## Projektváz

- `preprocessing/` letöltés, parse, chunk, index, mintaadat
- `backend/` FastAPI API + DB
- `agent/` LangGraph állapotgép
- `ui/` Streamlit felület
- `eval/` referencia-mentes kiértékelés
- `config/` policy és runtime konfig
- `data/` lokális adatok
- `docs/` DPIA és egyéb dokumentáció
