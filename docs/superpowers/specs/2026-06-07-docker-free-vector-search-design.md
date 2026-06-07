# Docker-mentes vektoros keresés — tervezési dokumentum

- **Dátum:** 2026-06-07
- **Branch:** `vector_search`
- **Státusz:** jóváhagyott terv (implementáció előtt)

## 1. Probléma és cél

A jelenlegi állapotban a RAG-lánc három ponton hiányos:

1. **Vektoradatbázis Docker-függő.** A `preprocessing/index.py` és a `backend/retrieval.py` egy hálózaton futó Qdrant-ra (`http://localhost:6333`) támaszkodik, amelyet a `docker-compose.yml` indít. Docker nélkül a Qdrant nem érhető el, a kód csendben a lokális fallback-re esik vissza.
2. **Az embedding nem valódi.** A `deterministic_embedding` egy 64 dimenziós, SHA256-alapú bag-of-words hash — nem szemantikus. A tervben/configban szereplő `text-embedding-3-large` sehol nincs ténylegesen meghívva.
3. A `chunks.jsonl` (51 035 chunk, 32 dokumentum) ténylegesen elkészül, és a `hybrid_local` keresés működik, de szemantikus minőség nélkül.

**Cél:** Docker nélkül futtatható rendszer, amely valódi szemantikus embeddinggel (OpenAI `text-embedding-3-large`) tölti fel és kérdezi le a vektorokat egy **beágyazott, helyi fájlalapú Qdrant**-ban, és minden hibánál / hiányzó API-kulcsnál csendben visszaesik a meglévő `hybrid_local` keresésre.

## 2. Döntések (jóváhagyva)

| Téma | Döntés | Elvetett alternatívák |
|---|---|---|
| Embedding | OpenAI `text-embedding-3-large` (felhő), közös interfész mögött | lokális fastembed/bge-m3; hash placeholder megtartása |
| Vektortár | `qdrant-client` **beágyazott helyi mód** (`path=`) | saját numpy-tár; sqlite-vec |
| Fallback | hiányzó kulcs/hálózat/hiba → csendes visszaesés `hybrid_local`-ra | kemény hiba kulcs nélkül |
| Embedding-cache | sqlite-alapú cache (belevéve) | nincs cache |

**Kulcsbelátás:** a `qdrant-client` már függőség, és támogatja a beágyazott `path=` módot — így a Docker-mentesség a vektortároláshoz **nem igényel új csomagot**, csak az `openai` csomag kerül be az embeddinghez.

## 3. Architektúra

```
PDF → parse.py (chunkok) → embedding.py ──┐
                                          ├─→ index.py → Qdrant (helyi fájl: data/qdrant_local/)
query → embedding.py (embed_query) ───────┘            ↓
                          retrieval.py → szemantikus keresés (ha OpenAI mód aktív)
                                       → hybrid_local fallback (egyébként / hibánál)
```

A `docker-compose.yml`-ben a `qdrant` volt az egyetlen profile nélkül (alapból) futó szolgáltatás; az `ollama` és a `langfuse` már most is opcionális profile-ök mögött vannak. A Qdrant beágyazásával az **alapfutáshoz semmilyen konténer nem szükséges**.

## 4. Komponensek

### 4.1 `preprocessing/embedding.py` (új modul)

A közös embedding-interfész, amely elrejti a provider-választást a hívók elől.

**Publikus felület:**

- `embed_documents(texts: list[str]) -> list[list[float]]` — több szöveg embeddingje, OpenAI esetén kötegelve (batch méret pl. 128), cache-eléssel.
- `embed_query(text: str) -> list[float]` — egyetlen lekérdezés embeddingje.
- `active_mode() -> str` — `"openai"` vagy `"deterministic"`.
- `vector_size() -> int` — az aktív mód vektor-dimenziója (`text-embedding-3-large` = 3072, vagy a `openai_embed_dim` ha be van állítva; determinisztikus = 64).

**Mód-választás logikája:**

- Ha `settings.provider != "onprem"` **és** `settings.openai_api_key` nem üres → `openai` mód.
- Egyébként → `deterministic` mód (a meglévő `deterministic_embedding`-et hívja).

**OpenAI hívás:**

- A hivatalos `openai` Python SDK-val, `client.embeddings.create(model=..., input=[...], dimensions=...)`.
- A `dimensions` paramétert csak akkor küldi, ha `settings.openai_embed_dim` be van állítva (egyébként a modell alap 3072).
- Hálózati / rate-limit / egyéb hibák felfelé propagálódnak (a hívó — index vagy retrieval — kezeli fallback-kel).

**Embedding-cache:**

- sqlite fájl: `data/processed/embedding_cache.db`.
- Tábla: `embedding_cache(key TEXT PRIMARY KEY, dim INTEGER, vector BLOB)`.
- Kulcs: `sha256(f"{model}:{dimensions}:{text}")`.
- A vektor float32 bájttömbként tárolva (`struct`/`array`).
- `embed_documents` cache-hit esetén nem hív API-t; csak a hiányzókat kéri le, majd elmenti.
- Csak `openai` módban használt (a determinisztikus úgyis olcsó és tiszta függvény).

### 4.2 `preprocessing/index.py` (módosul)

- A `deterministic_embedding` közvetlen hívása helyett `embedding.embed_documents(...)`.
- `VECTOR_SIZE` konstans helyett dinamikus dimenzió: `embedding.vector_size()`.
- `QdrantClient(url=...)` helyett a settings szerint:
  - `qdrant_mode == "local"` → `QdrantClient(path=settings.qdrant_path)`.
  - `qdrant_mode == "server"` → `QdrantClient(url=settings.qdrant_url)` (visszafelé kompatibilitás).
- `ensure_collection`: ha a kollekció létezik, de a vektor-dimenziója eltér a kívánttól (modellváltás), újra létrehozza.
- Minden chunk payloadjába bekerül a `content_hash` (`sha256(text)`) — metaadatként és jövőbeli diffhez.
- A point ID determinisztikus a `chunk_id`-ből (`uuid5(NAMESPACE_URL, chunk_id)`), így az upsert **idempotens** (ugyanaz a chunk mindig ugyanazt a pontot frissíti).
- `index_chunks` egy `force: bool = False` paramétert kap: ez az **embedding-cache megkerülését** vezérli (`force=True` → újra-embeddel API-ból). A pontok feltöltése mindig teljes és idempotens; a költségmegtakarítást az embedding-cache adja, nem külön diff-logika (YAGNI).
- `index_chunks` opcionális `client` paramétert is kap (tesztelhetőség / a helyi mód fájl-lockja miatt); ha maga hozza létre a klienst, a végén lezárja.

### 4.3 `backend/retrieval.py` (módosul)

- `search_qdrant`:
  - A helyi klienst használja (`path=` mód, settings szerint), `timeout` csak server módban értelmezett.
  - `embedding.embed_query(query)` a vektorhoz.
- `retrieve`:
  - Ha `embedding.active_mode() == "openai"` → megpróbálja a Qdrant szemantikus keresést.
  - Egyébként **egyből** `hybrid_local` (a determinisztikus hash-vektorral nincs értelme a Qdrantnak; a `hybrid_local` sparse + dense kombinációja jobb).
  - Bármely Qdrant/embedding hiba → `hybrid_local`. Ez a védőháló már létezik, megmarad.
- A visszaadott `retrieval_mode` értékek: `qdrant_semantic`, `hybrid_local`, `empty`.

### 4.4 `config/settings.py` (módosul)

Új mezők:

- `qdrant_mode: str = os.getenv("QDRANT_MODE", "local")` — `local` vagy `server`.
- `qdrant_path: str = os.getenv("QDRANT_PATH", "data/qdrant_local")`.
- `openai_embed_dim: int | None` — `os.getenv("OPENAI_EMBED_DIM")`, ha üres akkor `None`.

### 4.5 `backend/reindex_service.py` (módosul)

A visszaadott riportba bekerül:

- `embedding_mode`: `embedding.active_mode()` (`openai`/`deterministic`).
- `embedding_dim`: `embedding.vector_size()`.

Így a `/reindex` válaszából egyértelmű, valódi vagy fallback embedding ment-e.

### 4.6 `backend/router.py` (apró módosítás)

A `get_embed_profile()` a tényleges aktív módot tükrözze (pl. `cloud/text-embedding-3-large` vagy `local/deterministic-hash-v1`), összhangban az `embedding.active_mode()`-dal.

## 5. Adatfolyam és hibakezelés

**Indexelés (`run_reindex`):**
1. manifest építés → parse → `chunks.jsonl`.
2. `embedding.embed_documents` (cache + batch) → vektorok.
3. helyi Qdrant kollekció biztosítása (dimenzió-ellenőrzéssel) → upsert.
4. Ha nincs kulcs (`deterministic` mód): a Qdrant-indexelés kihagyható vagy determinisztikus vektorokkal történik, de a lekérdezés úgyis `hybrid_local` — konzisztens állapot.
5. Bármely embedding/Qdrant hiba → `qdrant_status="failed: ..."`, a pipeline többi része (chunkok, derive) lefut.

**Lekérdezés:** lásd 4.3 — minden út végén garantáltan van eredmény vagy `empty`, a rendszer sosem dől el.

## 6. Tesztelés

Új / bővített tesztek (valódi API-hívás nélkül, mockolva):

- `tests/test_embedding.py` (új):
  - determinisztikus mód stabil és normált vektort ad;
  - `active_mode`/`vector_size` helyes a settings függvényében (monkeypatch);
  - OpenAI ág mockolt klienssel (nincs valódi hálózat);
  - cache hit/miss: második hívás nem hív API-t.
- `tests/test_ingest_index.py` (bővítés): helyi (`path=`, `tmp_path`) módú kollekció-építés és upsert; dimenzió-recreate.
- `tests/test_retrieval.py` / `tests/test_retrieve_endpoint.py` (bővítés): szemantikus út mockolt embeddinggel; fallback, ha nincs kulcs ill. ha a Qdrant hibázik.
- A meglévő `search_chunks` / `hybrid_local` tesztek érintetlenül futnak.

## 7. Függőségek és konfiguráció

- `requirements.txt`: `+ openai`. (`qdrant-client` marad; nincs új vektor-csomag.)
- `.env.example`: `+ QDRANT_MODE=local`, `+ QDRANT_PATH=data/qdrant_local`, `+ OPENAI_EMBED_DIM=` (üres), magyarázó komment a Docker-mentes alapfutásról.
- `.gitignore`: `+ data/qdrant_local/`, `+ data/processed/embedding_cache.db`.
- `docker-compose.yml`: a `qdrant` szolgáltatás `profiles: [server]` alá kerül + komment, hogy alapból (beágyazott mód) nem kell.
- `README.md`: rövid frissítés a Docker-mentes futtatásról (opcionális, ha belefér).

## 8. Hatókörön kívül (YAGNI)

- Lokális (on-prem) valódi embedding-modell (fastembed/bge-m3) integrációja — most csak OpenAI + determinisztikus fallback.
- A `langfuse`/`ollama` szolgáltatások változatlanok (már most opcionális profile-ök).
- Sparse vektor natív Qdrant-indexelése — a sparse ág továbbra is a `hybrid_local`-ban él.

## 9. Visszafelé kompatibilitás

- A `QDRANT_MODE=server` + `QDRANT_URL` továbbra is működik (aki akar, futtathat külső Qdrant-ot).
- A `deterministic_embedding`, `search_chunks`, `hybrid_local` megmarad — a fallback rájuk épül.
- API-kulcs nélkül a rendszer pontosan a mai viselkedést adja (csak tisztább úton).
