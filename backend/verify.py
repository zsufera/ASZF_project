from __future__ import annotations

from typing import Any

GROUNDING_TOKEN_OVERLAP = 0.3


def normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _token_overlap(quote: str, draft_tokens: set[str]) -> float:
    quote_tokens = set(normalize(quote).split())
    if not quote_tokens:
        return 0.0
    return len(quote_tokens & draft_tokens) / len(quote_tokens)


def verify_draft(
    draft_body_masked: str,
    chunks: list[dict[str, Any]],
    mandatory_refs: list[str],
    citations: list[str] | None = None,
) -> dict[str, Any]:
    normalized_draft = normalize(draft_body_masked)
    draft_tokens = set(normalized_draft.split())
    chunk_by_id = {str(chunk.get("chunk_id")): chunk for chunk in chunks if chunk.get("chunk_id")}
    claims: list[dict[str, Any]] = []
    grounded_chunk_ids: set[str] = set()

    if citations is not None:
        for citation in citations:
            cid = str(citation)
            chunk = chunk_by_id.get(cid)
            quote = str(chunk.get("quote", "")) if chunk else ""
            grounded = chunk is not None and _token_overlap(quote, draft_tokens) >= GROUNDING_TOKEN_OVERLAP
            if grounded:
                grounded_chunk_ids.add(cid)
            claims.append({"claim": quote or cid, "grounded": grounded, "chunk_id": cid})
    else:
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
