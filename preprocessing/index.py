from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import threading
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from config.settings import settings
from preprocessing.embedding import embed_documents, vector_size


DEFAULT_CHUNKS_PATH = Path("data/processed/chunks.jsonl")
DEFAULT_COLLECTION = "aszf_chunks"
VECTOR_SIZE = 64
TOKEN_PATTERN = re.compile(r"[\wáéíóöőúüűÁÉÍÓÖŐÚÜŰ]+", re.UNICODE)


def load_chunks(chunks_path: Path = DEFAULT_CHUNKS_PATH) -> list[dict[str, Any]]:
    if not chunks_path.exists():
        return []
    chunks: list[dict[str, Any]] = []
    with chunks_path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                chunks.append(json.loads(stripped))
    return chunks


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def tokenize(text: str) -> list[str]:
    return [fold_text(token) for token in TOKEN_PATTERN.findall(text)]


def sparse_score(query: str, text: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
    overlap = query_tokens & text_tokens
    return len(overlap) / len(query_tokens)


def quote_text(text: str, max_chars: int = 500) -> str:
    normalized = " ".join(text.split())
    return normalized[:max_chars]


def search_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    service_provider: str | None = None,
    dok_tipus: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        if service_provider and chunk.get("szolgaltato") != service_provider:
            continue
        if dok_tipus and chunk.get("dok_tipus") != dok_tipus:
            continue
        score = sparse_score(query, chunk.get("text", ""))
        if score <= 0:
            continue
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "quote": quote_text(chunk.get("text", "")),
            "score": score,
            "dok_tipus": chunk.get("dok_tipus"),
            "paragrafus": chunk.get("paragrafus_szam"),
            "szolgaltato": chunk.get("szolgaltato"),
            "dok_cim": chunk.get("dok_cim"),
            "oldalszam": chunk.get("oldalszam"),
            "cross_refs": chunk.get("cross_refs", []),
        }
        for score, chunk in scored[:limit]
    ]


def deterministic_embedding(text: str, vector_size: int = VECTOR_SIZE) -> list[float]:
    vector = [0.0] * vector_size
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % vector_size
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, str(chunk_id)))


def make_client() -> QdrantClient:
    if settings.qdrant_mode == "local":
        return QdrantClient(path=settings.qdrant_path)
    return QdrantClient(url=settings.qdrant_url)


# ---------------------------------------------------------------------------
# Process-level singleton — helyi módban a HNSW index ~615 MB-os fájlból tölt;
# minden egyes make_client() + close() ciklus újra betölti. A singleton egyszer
# nyitja meg és folyamatosan életben tartja a backend folyamat alatt.
# ---------------------------------------------------------------------------
_shared_client: QdrantClient | None = None
_shared_client_lock = threading.Lock()


def get_shared_client() -> QdrantClient:
    """Return a process-level singleton QdrantClient.

    Local mode: avoids reloading the HNSW index on every retrieval call.
    Server mode: reuses the HTTP connection pool.
    Thread-safe double-checked locking a párhuzamos inicializálás ellen.
    """
    global _shared_client
    if _shared_client is None:
        with _shared_client_lock:
            if _shared_client is None:
                _shared_client = make_client()
    return _shared_client


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Index ASZF chunks into Qdrant.")
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS_PATH))
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--skip-qdrant", action="store_true")
    args = parser.parse_args()

    chunks = load_chunks(Path(args.chunks))
    if args.skip_qdrant:
        print(f"Loaded {len(chunks)} chunk(s); Qdrant indexing skipped.")
        return

    indexed = index_chunks(chunks=chunks, collection_name=args.collection)
    print(f"Indexed {indexed} chunk(s) into Qdrant collection '{args.collection}'.")


if __name__ == "__main__":
    main()
