from __future__ import annotations

from typing import Any


def normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def verify_draft(
    draft_body_masked: str,
    chunks: list[dict[str, Any]],
    mandatory_refs: list[str],
) -> dict[str, Any]:
    normalized_draft = normalize(draft_body_masked)
    claims: list[dict[str, Any]] = []
    grounded_chunk_ids: set[str] = set()

    for chunk in chunks:
        quote = str(chunk.get("quote", "")).strip()
        chunk_id = chunk.get("chunk_id")
        if not quote or not chunk_id:
            continue
        grounded = normalize(quote) in normalized_draft
        if grounded:
            grounded_chunk_ids.add(str(chunk_id))
        claims.append({"claim": quote, "grounded": grounded, "chunk_id": chunk_id})

    ungrounded_count = sum(1 for claim in claims if not claim["grounded"])
    missing_mandatory = [ref for ref in mandatory_refs if ref not in grounded_chunk_ids]
    warning = None
    if ungrounded_count or missing_mandatory:
        warning = "A draft nem teljesen forrásolt vagy kötelező hivatkozás hiányzik."

    return {
        "claims": claims,
        "ungrounded_count": ungrounded_count,
        "missing_mandatory": missing_mandatory,
        "warning": warning,
    }
