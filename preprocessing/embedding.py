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


def embed_query(text: str) -> list[float]:
    return embed_documents([text], use_cache=False)[0]
