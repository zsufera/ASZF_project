# Docker-free Vector Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Docker-based Qdrant with embedded (local-file) Qdrant and wire real OpenAI `text-embedding-3-large` embeddings behind a shared interface, with silent fallback to the existing `hybrid_local` search when no API key / network is available.

**Architecture:** A new `preprocessing/embedding.py` module owns provider selection (OpenAI vs deterministic hash), batching, and a sqlite embedding cache. `index.py` and `retrieval.py` call this interface and use `QdrantClient(path=...)` (local mode) instead of a URL. Any embedding/Qdrant failure or missing key falls back to `hybrid_local`, which reads `chunks.jsonl` directly.

**Tech Stack:** Python 3.11+, `qdrant-client` (local/embedded mode — already a dependency), `openai` (new), `sqlite3` (stdlib), `pytest`, `pymupdf`.

**Spec:** `docs/superpowers/specs/2026-06-07-docker-free-vector-search-design.md`

---

## File Structure

- **Create** `preprocessing/embedding.py` — shared embedding interface: `active_mode()`, `vector_size()`, `embed_documents()`, `embed_query()`, sqlite cache, OpenAI batching.
- **Create** `tests/test_embedding.py` — embedding module tests (mocked OpenAI, cache, fallback).
- **Modify** `config/settings.py` — add `qdrant_mode`, `qdrant_path`, `openai_embed_dim`.
- **Modify** `preprocessing/index.py` — local-mode client, dynamic dimension, `content_hash`, stable point IDs, embedding interface, `force`/`client` params.
- **Modify** `backend/retrieval.py` — semantic search via `embed_query` + local client; skip Qdrant in deterministic mode; `qdrant_semantic` mode label.
- **Modify** `backend/reindex_service.py` — report `embedding_mode` and `embedding_dim`.
- **Modify** `backend/router.py` — `get_embed_profile()` reflects active mode.
- **Modify** `tests/test_ingest_index.py` — add local-mode index test.
- **Modify** `tests/test_retrieval.py` — add semantic + fallback tests.
- **Modify** `requirements.txt`, `.env.example`, `.gitignore`, `docker-compose.yml`.

> **Note on circular imports:** `embedding.py` must NOT import `preprocessing.index` at module top level (index imports embedding). It imports `deterministic_embedding` lazily inside functions.

---

## Task 1: Settings — local Qdrant + embedding dimension config

**Files:**
- Modify: `config/settings.py`
- Test: `tests/test_settings_vector.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_settings_vector.py`:

```python
from config.settings import Settings


def test_settings_have_local_qdrant_defaults():
    s = Settings()
    assert s.qdrant_mode == "local"
    assert s.qdrant_path == "data/qdrant_local"
    assert s.openai_embed_dim is None


def test_openai_embed_dim_parsed_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_EMBED_DIM", "1024")
    # Settings reads env at instantiation via the field defaults; re-import fresh
    import importlib
    import config.settings as settings_module

    importlib.reload(settings_module)
    assert settings_module.Settings().openai_embed_dim == 1024
    monkeypatch.delenv("OPENAI_EMBED_DIM", raising=False)
    importlib.reload(settings_module)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings_vector.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'qdrant_mode'`

- [ ] **Step 3: Add the fields**

In `config/settings.py`, inside the `Settings` dataclass, add after the `qdrant_url` line:

```python
    qdrant_mode: str = os.getenv("QDRANT_MODE", "local")
    qdrant_path: str = os.getenv("QDRANT_PATH", "data/qdrant_local")
    openai_embed_dim: int | None = (
        int(os.environ["OPENAI_EMBED_DIM"]) if os.getenv("OPENAI_EMBED_DIM") else None
    )
```

Note: `from __future__ import annotations` is not present in this file; `int | None` as a default-valued annotation is evaluated at class-definition time but only the default expression runs, not the annotation — this is valid on Python 3.10+. The project targets 3.11+.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings_vector.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add config/settings.py tests/test_settings_vector.py
git commit -m "feat(config): add local Qdrant mode and embedding dimension settings"
```

---

## Task 2: Embedding module — deterministic mode + mode/size detection

**Files:**
- Create: `preprocessing/embedding.py`
- Test: `tests/test_embedding.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_embedding.py`:

```python
import preprocessing.embedding as emb
from config.settings import settings


def test_deterministic_mode_when_no_key(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert emb.active_mode() == "deterministic"
    assert emb.vector_size() == 64

    vectors = emb.embed_documents(["számlázási kifogás"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 64


def test_onprem_provider_is_deterministic(monkeypatch):
    monkeypatch.setattr(settings, "provider", "onprem")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    assert emb.active_mode() == "deterministic"


def test_openai_mode_detection(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_dim", None)
    assert emb.active_mode() == "openai"
    assert emb.vector_size() == 3072
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_embedding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preprocessing.embedding'`

- [ ] **Step 3: Create the module (deterministic + detection only)**

Create `preprocessing/embedding.py`:

```python
from __future__ import annotations

import hashlib
import sqlite3
import struct
from pathlib import Path

from config.settings import settings

DETERMINISTIC_SIZE = 64
DEFAULT_OPENAI_DIM = 3072
OPENAI_BATCH_SIZE = 128
EMBED_CACHE_PATH = Path("data/processed/embedding_cache.db")


def active_mode() -> str:
    """Return 'openai' when a cloud key is configured, else 'deterministic'."""
    if settings.provider != "onprem" and settings.openai_api_key:
        return "openai"
    return "deterministic"


def vector_size() -> int:
    if active_mode() == "openai":
        return settings.openai_embed_dim or DEFAULT_OPENAI_DIM
    return DETERMINISTIC_SIZE


def _deterministic_one(text: str) -> list[float]:
    # Lazy import avoids a circular import (index imports this module).
    from preprocessing.index import deterministic_embedding

    return deterministic_embedding(text)


def embed_documents(texts: list[str], use_cache: bool = True) -> list[list[float]]:
    if not texts:
        return []
    if active_mode() == "deterministic":
        return [_deterministic_one(text) for text in texts]
    raise NotImplementedError  # OpenAI path added in Task 3


def embed_query(text: str) -> list[float]:
    return embed_documents([text], use_cache=False)[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_embedding.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add preprocessing/embedding.py tests/test_embedding.py
git commit -m "feat(embedding): add shared interface with deterministic mode and detection"
```

---

## Task 3: Embedding module — OpenAI path + sqlite cache

**Files:**
- Modify: `preprocessing/embedding.py`
- Test: `tests/test_embedding.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_embedding.py`:

```python
import pytest


def test_openai_embed_uses_client_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_model", "text-embedding-3-large")
    monkeypatch.setattr(settings, "openai_embed_dim", 4)
    monkeypatch.setattr(emb, "EMBED_CACHE_PATH", tmp_path / "cache.db")

    calls = {"count": 0}

    def fake_embed(texts):
        calls["count"] += 1
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    monkeypatch.setattr(emb, "_openai_embed", fake_embed)

    first = emb.embed_documents(["alpha", "beta"])
    assert calls["count"] == 1
    assert len(first) == 2
    assert first[0][0] == pytest.approx(0.1, rel=1e-4)

    # Second call: both texts cached, no new API call.
    second = emb.embed_documents(["alpha", "beta"])
    assert calls["count"] == 1
    assert second[1][3] == pytest.approx(0.4, rel=1e-4)


def test_openai_partial_cache_only_embeds_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_dim", 4)
    monkeypatch.setattr(emb, "EMBED_CACHE_PATH", tmp_path / "cache.db")

    sent = []

    def fake_embed(texts):
        sent.append(list(texts))
        return [[0.5, 0.5, 0.5, 0.5] for _ in texts]

    monkeypatch.setattr(emb, "_openai_embed", fake_embed)

    emb.embed_documents(["alpha"])
    emb.embed_documents(["alpha", "gamma"])
    # First call embedded ["alpha"], second only ["gamma"].
    assert sent == [["alpha"], ["gamma"]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_embedding.py -v`
Expected: FAIL — `NotImplementedError` (and `_openai_embed` not yet defined for monkeypatch attr to make sense — the new tests fail).

- [ ] **Step 3: Implement OpenAI path + cache**

In `preprocessing/embedding.py`, replace the `embed_documents` function and add the helpers below it:

```python
def _cache_key(model: str, dim: int | None, text: str) -> str:
    return hashlib.sha256(f"{model}:{dim}:{text}".encode("utf-8")).hexdigest()


def _cache_connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS embedding_cache "
        "(key TEXT PRIMARY KEY, dim INTEGER, vector BLOB)"
    )
    return conn


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _unpack(blob: bytes) -> list[float]:
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def _openai_embed(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    kwargs = {"model": settings.openai_embed_model, "input": texts}
    if settings.openai_embed_dim:
        kwargs["dimensions"] = settings.openai_embed_dim
    response = client.embeddings.create(**kwargs)
    return [item.embedding for item in response.data]


def embed_documents(texts: list[str], use_cache: bool = True) -> list[list[float]]:
    if not texts:
        return []
    if active_mode() == "deterministic":
        return [_deterministic_one(text) for text in texts]

    model = settings.openai_embed_model
    dim = settings.openai_embed_dim
    keys = [_cache_key(model, dim, text) for text in texts]
    results: list[list[float] | None] = [None] * len(texts)

    conn = _cache_connect(EMBED_CACHE_PATH) if use_cache else None
    if conn is not None:
        for idx, key in enumerate(keys):
            row = conn.execute(
                "SELECT vector FROM embedding_cache WHERE key = ?", (key,)
            ).fetchone()
            if row is not None:
                results[idx] = _unpack(row[0])
    missing = [idx for idx, value in enumerate(results) if value is None]

    for start in range(0, len(missing), OPENAI_BATCH_SIZE):
        batch_idx = missing[start : start + OPENAI_BATCH_SIZE]
        vectors = _openai_embed([texts[i] for i in batch_idx])
        for i, vector in zip(batch_idx, vectors, strict=True):
            results[i] = list(vector)
            if conn is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO embedding_cache (key, dim, vector) "
                    "VALUES (?, ?, ?)",
                    (keys[i], len(vector), _pack(list(vector))),
                )
    if conn is not None:
        conn.commit()
        conn.close()
    return [vector for vector in results if vector is not None]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_embedding.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add preprocessing/embedding.py tests/test_embedding.py
git commit -m "feat(embedding): add OpenAI embedding path with sqlite cache and batching"
```

---

## Task 4: Index — local-mode client, dynamic dimension, content_hash, stable IDs

**Files:**
- Modify: `preprocessing/index.py`
- Test: `tests/test_ingest_index.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ingest_index.py`:

```python
import preprocessing.index as index
from config.settings import settings


def test_index_chunks_local_mode_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "qdrant_mode", "local")
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qd"))
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")  # deterministic -> size 64

    chunks = [
        {"chunk_id": "c1", "szolgaltato": "ONE", "text": "számlázási kifogás kezelése"},
        {"chunk_id": "c2", "szolgaltato": "ONE", "text": "felmondás feltételei"},
    ]

    client = index.make_client()
    count = index.index_chunks(chunks, client=client)

    assert count == 2
    info = client.get_collection(index.DEFAULT_COLLECTION)
    assert info.config.params.vectors.size == 64
    # content_hash is attached to payloads
    points, _ = client.scroll(index.DEFAULT_COLLECTION, with_payload=True, limit=10)
    assert all("content_hash" in point.payload for point in points)
    client.close()


def test_point_id_is_stable_for_chunk_id():
    assert index.point_id("c1") == index.point_id("c1")
    assert index.point_id("c1") != index.point_id("c2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ingest_index.py -v`
Expected: FAIL — `AttributeError: module 'preprocessing.index' has no attribute 'make_client'`

- [ ] **Step 3: Update index.py**

In `preprocessing/index.py`:

1. Add imports near the top (after existing imports):

```python
import uuid

from preprocessing.embedding import embed_documents, vector_size
```

2. Add these helpers (after the `deterministic_embedding` function):

```python
def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, str(chunk_id)))


def make_client() -> QdrantClient:
    if settings.qdrant_mode == "local":
        return QdrantClient(path=settings.qdrant_path)
    return QdrantClient(url=settings.qdrant_url)
```

3. Replace `ensure_collection` with a dimension-aware version:

```python
def ensure_collection(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION,
    size: int | None = None,
) -> None:
    size = size or vector_size()
    for collection in client.get_collections().collections:
        if collection.name == collection_name:
            info = client.get_collection(collection_name)
            if info.config.params.vectors.size == size:
                return
            client.delete_collection(collection_name)
            break
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE),
    )
```

4. Replace `index_chunks` with:

```python
def index_chunks(
    chunks: list[dict[str, Any]],
    collection_name: str = DEFAULT_COLLECTION,
    force: bool = False,
    client: QdrantClient | None = None,
) -> int:
    if not chunks:
        return 0
    owns_client = client is None
    client = client or make_client()
    try:
        size = vector_size()
        ensure_collection(client, collection_name, size)
        texts = [chunk.get("text", "") for chunk in chunks]
        vectors = embed_documents(texts, use_cache=not force)
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            payload = dict(chunk)
            payload["content_hash"] = content_hash(chunk.get("text", ""))
            points.append(
                models.PointStruct(
                    id=point_id(chunk.get("chunk_id", "")),
                    vector=vector,
                    payload=payload,
                )
            )
        client.upsert(collection_name=collection_name, points=points)
        return len(points)
    finally:
        if owns_client:
            client.close()
```

Note: `VECTOR_SIZE = 64` constant stays (used by `deterministic_embedding`'s default). `make_client` and the `--skip-qdrant` flag in `main()` remain valid.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ingest_index.py -v`
Expected: PASS (all index tests pass, including the two pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add preprocessing/index.py tests/test_ingest_index.py
git commit -m "feat(index): embedded Qdrant local mode, dynamic dim, stable ids, content_hash"
```

---

## Task 5: Retrieval — semantic search via embedding interface + fallback

**Files:**
- Modify: `backend/retrieval.py`
- Test: `tests/test_retrieval.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_retrieval.py`:

```python
import json

import preprocessing.embedding as emb
import preprocessing.index as index
import backend.retrieval as retrieval
from config.settings import settings


def _write_chunks(tmp_path):
    rows = [
        {"chunk_id": "one-bill", "szolgaltato": "ONE", "dok_tipus": "ÁSZF",
         "paragrafus_szam": "3.1", "doc_id": "d1", "cross_refs": [],
         "text": "A számlázási kifogás bejelentése és kivizsgálása."},
        {"chunk_id": "one-term", "szolgaltato": "ONE", "dok_tipus": "ÁSZF",
         "paragrafus_szam": "5.2", "doc_id": "d1", "cross_refs": [],
         "text": "A szerződés felmondásának feltételei."},
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def test_retrieve_falls_back_to_hybrid_local_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")  # deterministic -> skip qdrant
    chunks_path = _write_chunks(tmp_path)

    result = retrieval.retrieve("számlázási kifogás", service_provider="ONE",
                                chunks_path=chunks_path)

    assert result["retrieval_mode"] == "hybrid_local"
    assert result["result_count"] >= 1


def test_retrieve_uses_semantic_when_openai(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_dim", 8)
    monkeypatch.setattr(settings, "qdrant_mode", "local")
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qd"))
    monkeypatch.setattr(emb, "EMBED_CACHE_PATH", tmp_path / "cache.db")

    def fake_embed(texts):
        # "kifogás"-bearing text gets a distinct vector so it ranks first.
        out = []
        for text in texts:
            if "kifogás" in text:
                out.append([1.0, 0, 0, 0, 0, 0, 0, 0])
            else:
                out.append([0, 1.0, 0, 0, 0, 0, 0, 0])
        return out

    monkeypatch.setattr(emb, "_openai_embed", fake_embed)

    chunks_path = _write_chunks(tmp_path)
    rows = index.load_chunks(chunks_path)
    index.index_chunks(rows)  # builds local collection at qdrant_path

    result = retrieval.retrieve("kifogás", service_provider="ONE",
                                chunks_path=chunks_path)

    assert result["retrieval_mode"] == "qdrant_semantic"
    assert result["chunks"][0]["chunk_id"] == "one-bill"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_retrieval.py -v`
Expected: FAIL — `retrieval_mode` is `qdrant_hybrid`/`hybrid_local` mismatch, or `search_qdrant` still uses `deterministic_embedding`/URL client.

- [ ] **Step 3: Update retrieval.py**

In `backend/retrieval.py`:

1. Update imports — add at top with the other imports:

```python
from preprocessing.embedding import active_mode, embed_query
from preprocessing.index import DEFAULT_COLLECTION, make_client
```

(Keep the existing `from preprocessing.index import (...)` block; you may merge `DEFAULT_COLLECTION` into it instead of duplicating — ensure no duplicate names.)

2. Replace `search_qdrant` with:

```python
def search_qdrant(
    query: str,
    service_provider: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if active_mode() != "openai":
        return []
    try:
        from qdrant_client.http import models

        client = make_client()
        try:
            vector = embed_query(query)
            query_filter = None
            if service_provider:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="szolgaltato",
                            match=models.MatchValue(value=service_provider),
                        )
                    ]
                )
            hits = client.search(
                collection_name=DEFAULT_COLLECTION,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
            )
        finally:
            client.close()
        return [
            chunk_to_result(float(hit.score), hit.payload or {})
            | {"retrieval_source": "qdrant_semantic"}
            for hit in hits
        ]
    except Exception:
        return []
```

3. In `retrieve`, change the mode label. Find:

```python
    if qdrant_results:
        primary = qdrant_results
        retrieval_mode = "qdrant_hybrid"
```

Replace with:

```python
    if qdrant_results:
        primary = qdrant_results
        retrieval_mode = "qdrant_semantic"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_retrieval.py tests/test_retrieve_endpoint.py -v`
Expected: PASS (new tests pass; pre-existing retrieval tests still pass — they run without a key, so they use `hybrid_local`)

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval.py tests/test_retrieval.py
git commit -m "feat(retrieval): semantic Qdrant search via embedding interface with local fallback"
```

---

## Task 6: Reindex + router reporting

**Files:**
- Modify: `backend/reindex_service.py`
- Modify: `backend/router.py`
- Test: `tests/test_phase6_endpoints.py` (verify which file tests reindex) or add focused assertions in an existing reindex test.

- [ ] **Step 1: Write the failing test**

First locate the existing reindex test:

Run: `python -m pytest --collect-only -q | findstr /I reindex`

Then append to `tests/test_retrieval.py` a focused unit test (no HTTP needed):

```python
import backend.reindex_service as reindex_service


def test_reindex_reports_embedding_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")  # deterministic
    # Avoid touching real PDFs / Qdrant: stub the heavy steps.
    monkeypatch.setattr(reindex_service, "build_manifest", lambda: [])
    monkeypatch.setattr(reindex_service, "write_manifest", lambda items, path: None)
    monkeypatch.setattr(reindex_service, "parse_and_chunk",
                        lambda **kwargs: (0, 0))
    monkeypatch.setattr(reindex_service, "load_chunks", lambda path: [])
    monkeypatch.setattr(reindex_service, "index_chunks", lambda chunks: 0)
    monkeypatch.setattr(reindex_service, "derive_all", lambda: {})
    monkeypatch.setattr(
        reindex_service.Path, "read_text",
        lambda self, encoding=None: '{"document_count": 0, "documents": []}',
    )

    report = reindex_service.run_reindex()
    assert report["embedding_mode"] == "deterministic"
    assert report["embedding_dim"] == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_retrieval.py::test_reindex_reports_embedding_mode -v`
Expected: FAIL — `KeyError: 'embedding_mode'`

- [ ] **Step 3: Update reindex_service.py and router.py**

In `backend/reindex_service.py`:

1. Add import at top:

```python
from preprocessing.embedding import active_mode, vector_size
```

2. In the returned dict of `run_reindex`, add two keys (next to `qdrant_status`):

```python
        "embedding_mode": active_mode(),
        "embedding_dim": vector_size(),
```

In `backend/router.py`, replace `get_embed_profile`:

```python
def get_embed_profile() -> str:
    from preprocessing.embedding import active_mode

    if active_mode() == "openai":
        return f"cloud/{settings.openai_embed_model}"
    return "local/deterministic-hash-v1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_retrieval.py::test_reindex_reports_embedding_mode -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/reindex_service.py backend/router.py tests/test_retrieval.py
git commit -m "feat(reindex): report embedding mode and dimension; router reflects active embed profile"
```

---

## Task 7: Config — dependencies, env, gitignore, compose

**Files:**
- Modify: `requirements.txt`, `.env.example`, `.gitignore`, `docker-compose.yml`

- [ ] **Step 1: Add the `openai` dependency**

In `requirements.txt`, add a line after `qdrant-client`:

```
openai
```

Then install it:

Run: `python -m pip install openai`
Expected: successful install.

- [ ] **Step 2: Update `.env.example`**

Replace the `QDRANT_URL=...` line region with:

```
# Vektortár: alapból beágyazott (helyi fájl) mód, NEM kell Docker.
QDRANT_MODE=local
QDRANT_PATH=data/qdrant_local
# Külső szerverhez: QDRANT_MODE=server és a lenti URL.
QDRANT_URL=http://localhost:6333
```

And below the `OPENAI_EMBED_MODEL` line add:

```
# Opcionális embedding-dimenzió csökkentés (üres = modell alap, 3072).
OPENAI_EMBED_DIM=
```

- [ ] **Step 3: Update `.gitignore`**

Add two lines:

```
data/qdrant_local/
data/processed/embedding_cache.db
```

- [ ] **Step 4: Update `docker-compose.yml`**

Put the `qdrant` service behind a profile so it is no longer started by default. Change the `qdrant` service block to add:

```yaml
  qdrant:
    image: qdrant/qdrant:latest
    container_name: aszf_qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./data/qdrant_storage:/qdrant/storage
    profiles:
      - server   # Csak QDRANT_MODE=server esetén kell; alapból beágyazott mód fut.
```

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (no Docker/Qdrant server running).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore docker-compose.yml
git commit -m "chore: add openai dep, local-mode env defaults, gitignore, optional qdrant compose profile"
```

---

## Task 8: End-to-end smoke verification (no Docker)

**Files:**
- Read/use: `preprocessing/smoke_ingest.py`, `preprocessing/smoke_retrieve.py`

- [ ] **Step 1: Confirm deterministic (no-key) end-to-end works offline**

Run (PowerShell, ensure no `OPENAI_API_KEY` set):
```
python -m pytest -q
```
Expected: full suite green.

- [ ] **Step 2: Build a local index from the real chunks (deterministic mode)**

Run: `python -m preprocessing.index --chunks data/processed/chunks.jsonl`
Expected: prints `Indexed <N> chunk(s) into Qdrant collection 'aszf_chunks'.`, and a `data/qdrant_local/` directory is created (no Docker involved).

- [ ] **Step 3: Verify retrieval returns results from the local store**

Run: `python -m preprocessing.smoke_retrieve` (if it accepts a query arg, pass e.g. "számlázási kifogás"; otherwise inspect its output).
Expected: non-empty results; `retrieval_mode` is `hybrid_local` without a key (or `qdrant_semantic` if a key is exported).

- [ ] **Step 4: Commit any smoke-script tweaks (only if needed)**

```bash
git add -A
git commit -m "chore: verify Docker-free local vector pipeline end-to-end"
```

---

## Self-Review Notes

- **Spec coverage:** §4.1 embedding module → Tasks 2–3; §4.2 index → Task 4; §4.3 retrieval → Task 5; §4.4 settings → Task 1; §4.5 reindex + §4.6 router → Task 6; §7 config/deps → Task 7; §6 testing → distributed across tasks; verification → Task 8.
- **Naming consistency:** `make_client`, `point_id`, `content_hash`, `ensure_collection(client, name, size)`, `index_chunks(chunks, collection_name, force, client)`, `embed_documents(texts, use_cache)`, `embed_query(text)`, `active_mode()`, `vector_size()`, `EMBED_CACHE_PATH`, mode label `qdrant_semantic` — used identically across tasks.
- **Circular import:** handled via lazy import of `deterministic_embedding` inside `embedding.py`.
- **Local-mode file lock:** tests pass a shared `client` or run index/retrieve sequentially (each closes its client) to avoid the single-writer lock.
```
