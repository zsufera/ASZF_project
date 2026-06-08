---
name: rag-pipeline
description: Use when working on ÁSZF ingest or retrieval (chunking, indexing, embeddings, hybrid/semantic search, cross-references) or when retrieval quality / "no source found" issues come up. Explains the pipeline stages, the two embedding modes, and the retrieval contract.
---

# RAG ingest + retrieval pipeline

## Ingest sorrend (újraindexeléshez)
```powershell
python -m preprocessing.manifest        # data/ingest_manifest.json (hash-alapú dedup)
python -m preprocessing.parse           # data/processed/parsed_pages.jsonl + chunks.jsonl (hierarchikus, § szintű)
python -m preprocessing.index           # beágyazott helyi Qdrant-ba indexel (data/qdrant_local/)
python -m preprocessing.derive_params   # config/policies.yaml, mandatory_refs.yaml, disclaimer.yaml
python -m preprocessing.gen_emails      # minta-emailek
```
PDF-ek helye: `data/raw_pdfs/`. A `POST /reindex` end-to-end is futtatja (és invalidálja a chunk-cache-t: `backend/retrieval.py::refresh_chunk_cache`).

## Chunk-szerződés (minden chunk visszavezethető)
Kötelező mezők: `chunk_id`, `doc_id`, `source_file`, `szolgaltato`, `dok_tipus`, `dok_cim`, `oldalszam`, `paragrafus_szam`, `text`, `cross_refs`. A `index_chunks` a **teljes chunk-dictet** payloadként tárolja Qdrant-ban (`paragrafus_szam` is megvan a szemantikus találatoknál).

## Két embedding-mód (`preprocessing/embedding.py::active_mode`)
- **`openai`** (van `OPENAI_API_KEY`, `PROVIDER != onprem`): valódi `text-embedding-3-large` → helyi Qdrant HNSW szemantikus keresés (`qdrant_semantic`), opcionális `szolgaltato`-szűrővel.
- **`deterministic`** (nincs kulcs / onprem / tesztek): a `retrieve` a **hibrid lokális** úton megy (`hybrid_local`): `0.55*sparse + 0.45*dense` a `chunks.jsonl` fölött. **Figyelem:** a „dense" itt 64-dim hash (≈ zaj), tehát fallback módban a keresés gyakorlatilag **lexikai** — ne erre kalibrálj minőséget.

## Retrieval-szerződés (`backend/retrieval.py::retrieve`)
Visszaad: `{"chunks": [...], "retrieval_mode": "...", "result_count": N}`. Minden chunk-eredmény: `chunk_id`, `quote` (≤500 char), `score`, `dok_tipus`, `paragrafus`, `szolgaltato`, `dok_cim`, `oldalszam`, `cross_refs`, `retrieval_source`.
- **Cross-ref bővítés** (`resolve_cross_refs`): a talált § kereszthivatkozásait (azonos dokumentumon belül) max 3 extra chunk-ként behúzza (`retrieval_source: "cross_ref"`). Az ÁSZF önmagára hivatkozik — ez domain-specifikus erősség.
- **Szolgáltató-szűrés:** a négy szolgáltató dokumentumai ne keveredjenek (guardrails §5).

## Ismert korlátok / ahol javítani érdemes
- **Nincs valódi reranker** (a `rerank_chunks` csak a hibrid pontszám, nem cross-encoder).
- **Nincs query-rewrite** — a nyers, 400 karakterre vágott (maszkolt) üzenet a query.
- Egyetlen retrieval-pass, fix top-5. Gyenge találatnál nincs visszacsatolt „elég ez?" ellenőrzés → ilyenkor a downstream `insufficient`/eszkaláció lesz.
- A **kötelező hivatkozás** jelenlétét a `policy_map.build_policy_map` `chunk_id`/`paragrafus` alapján ellenőrzi (`config/mandatory_refs.yaml`); ha a kötelező § nincs a találatok közt → `missing_mandatory` → eszkaláció. Ha ez túl gyakran sül el, a **retrieval minőségét** kell javítani (rerank / query-rewrite / CRAG), nem az eszkalációs logikát kilazítani.

## Tesztelés
- Unit: `retrieve` deterministic módban menjen Qdrant nélkül is. Minimum elvárás: kérdés → ≥1 forrásos chunk `chunk_id` + idézet + `dok_tipus` mezővel.
- Qdrant/szemantikus utat **külön integrációs** jelöléssel és mockolt embeddinggel tesztelj, ne valódi API-val.
- Kis fixture, ne a teljes ~51k chunkos korpusz.
