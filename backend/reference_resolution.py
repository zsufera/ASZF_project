from __future__ import annotations

import re
from typing import Any

from preprocessing.index import fold_text

_doc_name_index_cache: dict[tuple[int, int], dict[tuple[str, str], str]] = {}
_paragraph_index_cache: dict[tuple[int, int], dict[tuple[str, str], dict[str, Any]]] = {}


def _cache_key(chunks: list[dict[str, Any]]) -> tuple[int, int]:
    return (id(chunks), len(chunks))

_PARAGRAPH_NUMBER = re.compile(r"\d+(?:\.\d+){0,4}")
# fájlnévből: "...2a_mobil_melleklet...", "..._3_melleklet...", "...1_sz_melleklet..."
_MELLEKLET_IN_FILENAME = re.compile(r"(\d+)\s*([ab]?)[a-z0-9_]*?mellekl")
# hint-ből: "2/A. számú melléklet", "3. számú melléklet"
_MELLEKLET_IN_HINT = re.compile(r"(\d+)\s*([ab]?)(?:/([ab]))?\.?\s*sz[áa]m[úu]?\s*mellekl")


def normalize_paragraph(value: str | None) -> str:
    if not value:
        return ""
    match = _PARAGRAPH_NUMBER.search(str(value))
    return match.group(0) if match else fold_text(str(value))


def _melleklet_keys(num: str, letter: str) -> set[str]:
    keys = {f"{num} melleklet"}
    if letter:
        keys |= {f"{num}{letter} melleklet", f"{num}/{letter} melleklet"}
    return keys


def _doc_keys_from_filename(source_file: str) -> set[str]:
    base = fold_text(str(source_file).replace("\\", "/").rsplit("/", 1)[-1])
    match = _MELLEKLET_IN_FILENAME.search(base)
    if not match:
        return set()
    return _melleklet_keys(match.group(1), match.group(2))


def _doc_keys_from_hint(doc_hint: str) -> set[str]:
    match = _MELLEKLET_IN_HINT.search(fold_text(doc_hint))
    if not match:
        return set()
    letter = match.group(2) or match.group(3) or ""
    return _melleklet_keys(match.group(1), letter)


def build_doc_name_index(chunks: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    """(szolgaltato, normalizált dok-név) -> doc_id. Kétértelmű kulcs (ütköző doc_id) eldobva."""
    cache_key = _cache_key(chunks)
    cached = _doc_name_index_cache.get(cache_key)
    if cached is not None:
        return cached
    index: dict[tuple[str, str], str] = {}
    ambiguous: set[tuple[str, str]] = set()
    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        szolg = chunk.get("szolgaltato") or ""
        if not doc_id:
            continue
        for key in _doc_keys_from_filename(chunk.get("source_file") or ""):
            k = (szolg, key)
            if k in ambiguous:
                continue
            existing = index.get(k)
            if existing is not None and existing != doc_id:
                del index[k]
                ambiguous.add(k)
            else:
                index[k] = doc_id
    _doc_name_index_cache[cache_key] = index
    return index


def build_paragraph_index(chunks: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """(doc_id, normalizált paragrafus) -> chunk (első nyer)."""
    cache_key = _cache_key(chunks)
    cached = _paragraph_index_cache.get(cache_key)
    if cached is not None:
        return cached
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        paragraph = normalize_paragraph(chunk.get("paragrafus_szam") or chunk.get("paragrafus"))
        if not doc_id or not paragraph:
            continue
        index.setdefault((doc_id, paragraph), chunk)
    _paragraph_index_cache[cache_key] = index
    return index


def resolve_reference(
    ref: dict[str, Any],
    source_chunk: dict[str, Any],
    doc_name_index: dict[tuple[str, str], str],
    paragraph_index: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any] | None:
    paragraph = normalize_paragraph(ref.get("paragraph"))
    if not paragraph:
        return None  # dok-szintű hivatkozás (paragrafus nélkül) — szándékosan nem oldjuk fel
    szolg = source_chunk.get("szolgaltato") or ""
    doc_hint = ref.get("doc_hint")
    if doc_hint:
        target_doc = None
        for key in _doc_keys_from_hint(doc_hint):
            candidate = doc_name_index.get((szolg, key))
            if candidate:
                target_doc = candidate
                break
        if not target_doc:
            return None
    else:
        target_doc = source_chunk.get("doc_id")

    exact = paragraph_index.get((target_doc, paragraph))
    if exact:
        return exact
    for (doc_id, para), chunk in paragraph_index.items():
        if doc_id == target_doc and para.startswith(paragraph + "."):
            return chunk
    return None


def reference_closure(
    seed_chunks: list[dict[str, Any]],
    all_chunks: list[dict[str, Any]],
    max_hops: int = 1,
    max_extra: int = 5,
) -> tuple[list[tuple[dict[str, Any], float]], list[dict[str, Any]]]:
    """1-hop referencia-lezárás: a seed chunkok hivatkozásait feloldja és behúzza.

    Visszatérés: (added, unresolved), ahol added = [(chunk, score), ...] (max_extra-ig),
    unresolved = a fel nem oldott hivatkozás-dictek. A behúzott score a seed score-ja - 0.05.
    """
    doc_name_index = build_doc_name_index(all_chunks)
    paragraph_index = build_paragraph_index(all_chunks)
    by_id = {str(c.get("chunk_id")): c for c in all_chunks if c.get("chunk_id")}
    seen = {str(c.get("chunk_id")) for c in seed_chunks if c.get("chunk_id")}

    added: list[tuple[dict[str, Any], float]] = []
    unresolved: list[dict[str, Any]] = []

    for seed in seed_chunks:
        source_chunk = by_id.get(str(seed.get("chunk_id")), seed)
        base_score = max(float(seed.get("score", 0.0)) - 0.05, 0.01)
        for ref in (source_chunk.get("cross_refs") or []):
            if len(added) >= max_extra:
                return added, unresolved
            target = resolve_reference(ref, source_chunk, doc_name_index, paragraph_index)
            if target is None:
                unresolved.append(ref)
                continue
            tid = str(target.get("chunk_id"))
            if tid in seen:
                continue
            seen.add(tid)
            added.append((target, base_score))
    return added, unresolved


def parent_context(
    seed_chunks: list[dict[str, Any]],
    all_chunks: list[dict[str, Any]],
    max_extra: int = 3,
) -> list[tuple[dict[str, Any], float]]:
    """Small-to-big: a top találatok közvetlen szülő §-át behúzza extra kontextusként.

    A szülő a paragrafus-prefixből adódik (5.5.1 -> 5.5), azonos dokumentumon belül.
    Visszatérés: [(parent_chunk, score), ...] (max_extra-ig, dedupolva). A score a seed - 0.03.
    """
    by_id = {str(c.get("chunk_id")): c for c in all_chunks if c.get("chunk_id")}
    paragraph_index = build_paragraph_index(all_chunks)
    seen = {str(c.get("chunk_id")) for c in seed_chunks if c.get("chunk_id")}

    added: list[tuple[dict[str, Any], float]] = []
    for seed in seed_chunks:
        if len(added) >= max_extra:
            break
        source = by_id.get(str(seed.get("chunk_id")))
        if not source:
            continue
        paragraph = normalize_paragraph(source.get("paragrafus_szam") or source.get("paragrafus"))
        if "." not in paragraph:
            continue  # felső szintű § — nincs szülő
        parent_paragraph = paragraph.rsplit(".", 1)[0]
        parent = paragraph_index.get((source.get("doc_id"), parent_paragraph))
        if not parent:
            continue
        pid = str(parent.get("chunk_id"))
        if pid in seen:
            continue
        seen.add(pid)
        added.append((parent, max(float(seed.get("score", 0.0)) - 0.03, 0.01)))
    return added
