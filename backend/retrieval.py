from __future__ import annotations

import math
import re
import threading
from typing import Any

from preprocessing.embedding import active_mode, embed_query
from preprocessing.index import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_COLLECTION,
    deterministic_embedding,
    fold_text,
    get_shared_client,
    load_chunks,
    quote_text,
    search_chunks,
    sparse_score,
    tokenize,
)

from backend.policy_map import category_mandatory_paragraphs, category_section_prefixes
from backend.reference_resolution import reference_closure
from config.settings import settings


HYBRID_SPARSE_WEIGHT = 0.55
HYBRID_DENSE_WEIGHT = 0.45

# ---------------------------------------------------------------------------
# In-memory chunk cache — a 28,5 MB-os chunks.jsonl beolvasása és 51 049 JSON
# sor parse-olása minden híváskor szükségtelen CPU/disk terhelés.
# Az újraindexelés (_refresh_chunk_cache) a /reindex endpoint hívja.
# ---------------------------------------------------------------------------
_chunk_cache: list[dict] | None = None
_chunk_cache_path: Path | None = None
_chunk_cache_lock = threading.Lock()


def _get_chunks(chunks_path: Path = DEFAULT_CHUNKS_PATH) -> list[dict]:
    """Return cached chunks; reload only if path changed or cache is empty.

    Thread-safe double-checked locking: több worker/szál egyszerre nem tölti be
    párhuzamosan a nagy chunks.jsonl-t.
    """
    global _chunk_cache, _chunk_cache_path
    if _chunk_cache is None or _chunk_cache_path != chunks_path:
        with _chunk_cache_lock:
            if _chunk_cache is None or _chunk_cache_path != chunks_path:
                _chunk_cache = load_chunks(chunks_path)
                _chunk_cache_path = chunks_path
    return _chunk_cache


def refresh_chunk_cache() -> None:
    """Invalidate the in-memory chunk cache (call after reindexing)."""
    global _chunk_cache
    _chunk_cache = None


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def dense_score(query: str, text: str) -> float:
    return cosine_similarity(deterministic_embedding(query), deterministic_embedding(text))


def hybrid_score(query: str, text: str, paragrafus: str | None = None) -> float:
    sparse = sparse_score(query, text)
    dense = dense_score(query, text)
    score = HYBRID_SPARSE_WEIGHT * sparse + HYBRID_DENSE_WEIGHT * dense
    if paragrafus and any(token in fold_text(paragrafus) for token in tokenize(query)):
        score += 0.05
    return min(score, 1.0)


def chunk_to_result(score: float, chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "quote": quote_text(chunk.get("text", "")),
        "score": round(score, 4),
        "dok_tipus": chunk.get("dok_tipus"),
        "paragrafus": chunk.get("paragrafus_szam"),
        "szolgaltato": chunk.get("szolgaltato"),
        "dok_cim": chunk.get("dok_cim"),
        "oldalszam": chunk.get("oldalszam"),
        "cross_refs": chunk.get("cross_refs", []),
        "source_file": chunk.get("source_file"),
        "retrieval_source": "hybrid_local",
    }


def rerank_chunks(query: str, chunks: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        score = hybrid_score(query, chunk.get("text", ""), chunk.get("paragrafus_szam"))
        if score <= 0:
            continue
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk_to_result(score, chunk) for score, chunk in scored[:limit]]


def _chunk_index(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(chunk.get("chunk_id")): chunk for chunk in chunks if chunk.get("chunk_id")}


def search_qdrant(
    query: str,
    service_provider: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if active_mode() != "openai":
        return []
    try:
        from qdrant_client.http import models

        # Singleton client: helyi módban a HNSW index betöltése csak egyszer
        # történik a process élettartama alatt, nem minden hívásnál.
        client = get_shared_client()
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
        response = client.query_points(
            collection_name=DEFAULT_COLLECTION,
            query=vector,
            query_filter=query_filter,
            limit=limit,
        )
        return [
            chunk_to_result(float(hit.score), hit.payload or {})
            | {"retrieval_source": "qdrant_semantic"}
            for hit in response.points
        ]
    except Exception:
        return []


def apply_category_boost(
    results: list[dict[str, Any]],
    section_prefixes: set[str],
    mandatory_paras: set[str],
) -> list[dict[str, Any]]:
    """A kategória szekciójába (felső szint) vagy kötelező §-ába eső találatokat felsúlyozza,
    majd újrarendezi. Pontos kötelező-§ egyezés erősebb boostot kap, mint a szekció-egyezés."""
    if not section_prefixes and not mandatory_paras:
        return results
    boosted: list[dict[str, Any]] = []
    for result in results:
        paragraph = str(result.get("paragrafus") or "")
        top = paragraph.split(".")[0].strip()
        score = float(result.get("score", 0.0))
        if paragraph in mandatory_paras:
            score = min(score + 0.2, 1.0)
        elif top and top in section_prefixes:
            score = min(score + 0.1, 1.0)
        boosted.append({**result, "score": round(score, 4)})
    boosted.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return boosted


def retrieve(
    query: str,
    service_provider: str | None = None,
    dok_tipus: str | None = None,
    limit: int = 5,
    chunks_path: Any = DEFAULT_CHUNKS_PATH,
    prefer_qdrant: bool = True,
    category: str | None = None,
) -> dict[str, Any]:
    all_chunks = _get_chunks(chunks_path)
    filtered = [
        chunk
        for chunk in all_chunks
        if (not service_provider or chunk.get("szolgaltato") == service_provider)
        and (not dok_tipus or chunk.get("dok_tipus") == dok_tipus)
    ]
    # Kategória-routinghoz nagyobb jelölt-pool, hogy a boost ténylegesen átrendezhessen.
    candidate_limit = limit * 4 if category else limit

    qdrant_results = search_qdrant(query, service_provider, candidate_limit) if prefer_qdrant else []
    if qdrant_results:
        primary = qdrant_results
        retrieval_mode = "qdrant_semantic"
    elif filtered:
        sparse_results = search_chunks(
            query=query,
            chunks=filtered,
            service_provider=service_provider,
            dok_tipus=dok_tipus,
            limit=candidate_limit,
        )
        if sparse_results:
            rescored = []
            by_id = _chunk_index(filtered)
            for item in sparse_results:
                chunk = by_id.get(str(item.get("chunk_id")), {})
                rescored.append(
                    chunk_to_result(
                        hybrid_score(query, chunk.get("text", ""), chunk.get("paragrafus_szam")),
                        chunk,
                    )
                )
            rescored.sort(key=lambda item: item["score"], reverse=True)
            primary = rescored[:candidate_limit]
        else:
            primary = rerank_chunks(query, filtered, limit=candidate_limit)
        retrieval_mode = "hybrid_local"
    else:
        primary = []
        retrieval_mode = "empty"

    if category:
        primary = apply_category_boost(
            primary,
            category_section_prefixes(category),
            category_mandatory_paragraphs(category),
        )
    primary = primary[:limit]

    added, unresolved = reference_closure(primary, all_chunks)
    expanded = list(primary)
    for chunk, score in added:
        expanded.append(chunk_to_result(score, chunk) | {"retrieval_source": "reference_closure"})
    return {
        "chunks": expanded,
        "retrieval_mode": retrieval_mode,
        "result_count": len(expanded),
        "unresolved_refs": unresolved,
    }
