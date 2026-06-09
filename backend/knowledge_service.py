from __future__ import annotations

from typing import Any

from preprocessing.index import DEFAULT_CHUNKS_PATH, fold_text, load_chunks, quote_text


def load_knowledge_chunks() -> list[dict[str, Any]]:
    return load_chunks(DEFAULT_CHUNKS_PATH)


def _public_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    paragraph = str(chunk.get("paragrafus_szam") or chunk.get("paragrafus") or "")
    return {
        "chunk_id": chunk.get("chunk_id"),
        "section": paragraph.split(".", 1)[0] if paragraph else "",
        "paragrafus": paragraph,
        "dok_tipus": chunk.get("dok_tipus"),
        "dok_cim": chunk.get("dok_cim"),
        "oldalszam": chunk.get("oldalszam"),
        "quote": quote_text(chunk.get("text", ""), max_chars=420),
        "cross_refs": chunk.get("cross_refs") or [],
        "source_file": chunk.get("source_file"),
    }


def knowledge_tree(limit: int = 250) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for chunk in load_knowledge_chunks():
        item = _public_chunk(chunk)
        section = item["section"] or "egyeb"
        group = grouped.setdefault(
            section,
            {
                "section": section,
                "label": f"{section}. szakasz" if section != "egyeb" else "Egyeb",
                "count": 0,
                "items": [],
            },
        )
        group["count"] += 1
        if len(group["items"]) < 20:
            group["items"].append(item)
    return sorted(grouped.values(), key=lambda item: item["section"])[:limit]


def knowledge_section(chunk_id: str) -> dict[str, Any] | None:
    for chunk in load_knowledge_chunks():
        if str(chunk.get("chunk_id")) == chunk_id:
            return _public_chunk(chunk) | {"text": chunk.get("text", "")}
    return None


def knowledge_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    folded_query = fold_text(query)
    if not folded_query:
        return []
    tokens = [token for token in folded_query.split() if len(token) > 1]
    scored: list[tuple[int, dict[str, Any]]] = []
    for chunk in load_knowledge_chunks():
        haystack = fold_text(
            " ".join(
                str(chunk.get(key) or "")
                for key in ("text", "paragrafus_szam", "dok_tipus", "dok_cim")
            )
        )
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [_public_chunk(chunk) | {"score": score} for score, chunk in scored[:limit]]
