# ASZF Q&A Agent (POC)

POC-level belső copilot telekom ügyfélszolgálathoz:
- ÁSZF-alapú forráshivatkozás
- válaszlevél-javaslat
- eszkalációs döntéstámogatás
- auditálható, human-in-the-loop működés

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

WAF vagy manuális beszerzés esetén másold a PDF-eket a `data/raw_pdfs/` mappába.

1. Manifest generálás:
   - `python -m preprocessing.manifest`
   - kimenet: `data/ingest_manifest.json`
2. PDF parse + hierarchikus chunkolás:
   - `python -m preprocessing.parse`
   - kimenetek:
     - `data/processed/parsed_pages.jsonl`
     - `data/processed/chunks.jsonl`

Ha nincs PDF a `data/raw_pdfs/` alatt, a manifest üres dokumentumlistával jön létre. A Qdrant indexelés a következő implementációs lépés.

## Projektváz

- `preprocessing/` letöltés, parse, chunk, index, mintaadat
- `backend/` FastAPI API + DB
- `agent/` LangGraph állapotgép
- `ui/` Streamlit felület
- `eval/` referencia-mentes kiértékelés
- `config/` policy és runtime konfig
- `data/` lokális adatok
- `docs/` DPIA és egyéb dokumentáció
