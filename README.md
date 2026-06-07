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

## Backend minimál flow

Az első vertikális backend sorrend:

1. `/classify` -> determinisztikus fallback kategória + konfidencia
2. `/retrieve` -> forrásos chunkok
3. `/policy-map` -> ÜI-nak mutatható szabályzat-térkép
4. `backend.escalation.decide_escalation()` -> eszkalációs döntési helper
5. `/draft` -> válaszjavaslat citationökkel és automata módban disclaimerrel
6. `/verify` -> groundedness és kötelező hivatkozás ellenőrzés

## Projektváz

- `preprocessing/` letöltés, parse, chunk, index, mintaadat
- `backend/` FastAPI API + DB
- `agent/` LangGraph állapotgép
- `ui/` Streamlit felület
- `eval/` referencia-mentes kiértékelés
- `config/` policy és runtime konfig
- `data/` lokális adatok
- `docs/` DPIA és egyéb dokumentáció
