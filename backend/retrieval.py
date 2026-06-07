from __future__ import annotations

import math
import re
from typing import Any

from preprocessing.embedding import active_mode, embed_query
from preprocessing.index import (
    DEFAULT_CHUNKS_PATH,
    DEFAULT_COLLECTION,
    deterministic_embedding,
    fold_text,
    load_chunks,
    make_client,
    quote_text,
    search_chunks,
    sparse_score,
    tokenize,
)

from config.settings import settings


REF_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+){0,4}")
HYBRID_SPARSE_WEIGHT = 0.55
HYBRID_DENSE_WEIGHT = 0.45
CROSS_REF_LIMIT = 3


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


def _normalize_ref(value: str) -> str:
    match = REF_NUMBER_PATTERN.search(value)
    return match.group(0) if match else fold_text(value)


def _chunk_index(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(chunk.get("chunk_id")): chunk for chunk in chunks if chunk.get("chunk_id")}


def _chunks_by_doc(chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        doc_id = str(chunk.get("doc_id") or "")
        grouped.setdefault(doc_id, []).append(chunk)
    return grouped


def resolve_cross_refs(
    results: list[dict[str, Any]],
    all_chunks: list[dict[str, Any]],
    max_extra: int = CROSS_REF_LIMIT,
) -> list[dict[str, Any]]:
    if not results:
        return results

    by_id = _chunk_index(all_chunks)
    by_doc = _chunks_by_doc(all_chunks)
    seen = {item["chunk_id"] for item in results if item.get("chunk_id")}
    expanded = list(results)

    for result in results:
        source_chunk = by_id.get(str(result.get("chunk_id")))
        if not source_chunk:
            continue
        doc_id = str(source_chunk.get("doc_id") or "")
        doc_chunks = by_doc.get(doc_id, [])
        for ref in source_chunk.get("cross_refs", []):
            if len(expanded) >= len(results) + max_extra:
                return expanded
            ref_key = _normalize_ref(ref)
            for candidate in doc_chunks:
                chunk_id = candidate.get("chunk_id")
                if not chunk_id or chunk_id in seen:
                    continue
                paragraph = str(candidate.get("paragrafus_szam") or "")
                if ref_key and (paragraph.startswith(ref_key) or ref_key in fold_text(paragraph)):
                    expanded.append(
                        chunk_to_result(max(result.get("score", 0.0) - 0.05, 0.01), candidate)
                        | {"retrieval_source": "cross_ref"}
                    )
                    seen.add(chunk_id)
                    break
    return expanded


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
            response = client.query_points(
                collection_name=DEFAULT_COLLECTION,
                query=vector,
                query_filter=query_filter,
                limit=limit,
            )
        finally:
            client.close()
        return [
            chunk_to_result(float(hit.score), hit.payload or {})
            | {"retrieval_source": "qdrant_semantic"}
            for hit in response.points
        ]
    except Exception:
        return []


def retrieve(
    query: str,
    service_provider: str | None = None,
    dok_tipus: str | None = None,
    limit: int = 5,
    chunks_path: Any = DEFAULT_CHUNKS_PATH,
    prefer_qdrant: bool = True,
) -> dict[str, Any]:
    all_chunks = load_chunks(chunks_path)
    filtered = [
        chunk
        for chunk in all_chunks
        if (not service_provider or chunk.get("szolgaltato") == service_provider)
        and (not dok_tipus or chunk.get("dok_tipus") == dok_tipus)
    ]

    qdrant_results = search_qdrant(query, service_provider, limit) if prefer_qdrant else []
    if qdrant_results:
        primary = qdrant_results
        retrieval_mode = "qdrant_semantic"
    elif filtered:
        sparse_results = search_chunks(
            query=query,
            chunks=filtered,
            service_provider=service_provider,
            dok_tipus=dok_tipus,
            limit=limit,
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
            primary = rescored[:limit]
        else:
            primary = rerank_chunks(query, filtered, limit=limit)
        retrieval_mode = "hybrid_local"
    else:
        primary = []
        retrieval_mode = "empty"

    expanded = resolve_cross_refs(primary, all_chunks)
    return {
        "chunks": expanded,
        "retrieval_mode": retrieval_mode,
        "result_count": len(expanded),
    }
