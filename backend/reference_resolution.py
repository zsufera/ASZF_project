from __future__ import annotations

import re
from typing import Any

from preprocessing.index import fold_text

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
    return index


def build_paragraph_index(chunks: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """(doc_id, normalizált paragrafus) -> chunk (első nyer)."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        paragraph = normalize_paragraph(chunk.get("paragrafus_szam") or chunk.get("paragrafus"))
        if not doc_id or not paragraph:
            continue
        index.setdefault((doc_id, paragraph), chunk)
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
