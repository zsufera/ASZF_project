from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from config.settings import settings


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


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


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


def ensure_collection(client: QdrantClient, collection_name: str = DEFAULT_COLLECTION) -> None:
    collections = client.get_collections().collections
    if any(collection.name == collection_name for collection in collections):
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )


def index_chunks(
    chunks: list[dict[str, Any]],
    qdrant_url: str = settings.qdrant_url,
    collection_name: str = DEFAULT_COLLECTION,
) -> int:
    if not chunks:
        return 0
    client = QdrantClient(url=qdrant_url)
    ensure_collection(client, collection_name)
    points = [
        models.PointStruct(
            id=idx,
            vector=deterministic_embedding(chunk.get("text", "")),
            payload=chunk,
        )
        for idx, chunk in enumerate(chunks)
    ]
    client.upsert(collection_name=collection_name, points=points)
    return len(points)


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
