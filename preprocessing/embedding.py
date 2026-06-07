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
