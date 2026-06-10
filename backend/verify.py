from __future__ import annotations

import logging
from typing import Any

from backend.llm import chat_json, llm_available, load_prompt
from config.settings import settings

logger = logging.getLogger(__name__)

VERIFY_SYSTEM = load_prompt("verify")


def normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _token_overlap(quote: str, draft_tokens: set[str]) -> float:
    quote_tokens = set(normalize(quote).split())
    if not quote_tokens:
        return 0.0
    return len(quote_tokens & draft_tokens) / len(quote_tokens)


def llm_verify_grounding(
    draft_body_masked: str,
    chunks: list[dict[str, Any]],
    citations: list[str],
) -> set[str] | None:
    """LLM-judge: a hivatkozott források közül melyeket NEM támasztja alá a forrásuk.

    Visszatérés: nem-megalapozott chunk_id-k halmaza, vagy None, ha az LLM-judge nem
    elérhető / nincs hivatkozás / hiba történt (ekkor a hívó a heurisztikára esik vissza).
    Egyetlen, kötegelt LLM-hívás (nem forrásonként).
    """
    if not (settings.llm_verify_enabled and llm_available()):
        return None
    chunk_by_id = {str(chunk.get("chunk_id")): chunk for chunk in chunks if chunk.get("chunk_id")}
    cited = [str(c) for c in citations if str(c) in chunk_by_id]
    if not cited:
        return None
    try:
        sources_block = "\n".join(f'- [{cid}] "{chunk_by_id[cid].get("quote", "")}"' for cid in cited)
        user = f'VÁLASZ:\n"""\n{draft_body_masked}\n"""\nFORRÁSOK:\n{sources_block}'
        data = chat_json(VERIFY_SYSTEM, user)
        raw = data.get("nem_megalapozott") or data.get("nem_megalapozott_chunk_idk") or []
        return {str(x) for x in raw if str(x) in chunk_by_id}
    except Exception:
        logger.exception("llm_verify_grounding failed; falling back to heuristic")
        return None


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
    verify_mode = "heuristic"

    llm_ungrounded = (
        llm_verify_grounding(draft_body_masked, chunks, citations) if citations is not None else None
    )

    if citations is not None and llm_ungrounded is not None:
        # LLM-judge út: a parafrázist is megalapozottnak ismeri fel (token-átfedés nélkül).
        verify_mode = "llm"
        for citation in citations:
            cid = str(citation)
            chunk = chunk_by_id.get(cid)
            quote = str(chunk.get("quote", "")) if chunk else ""
            grounded = chunk is not None and cid not in llm_ungrounded
            if grounded:
                grounded_chunk_ids.add(cid)
            claims.append({"claim": quote or cid, "grounded": grounded, "chunk_id": cid})
    elif citations is not None:
        # Heurisztikus fallback: token-átfedés a forrás-idézet és a draft között.
        for citation in citations:
            cid = str(citation)
            chunk = chunk_by_id.get(cid)
            quote = str(chunk.get("quote", "")) if chunk else ""
            grounded = chunk is not None and _token_overlap(quote, draft_tokens) >= settings.grounding_token_overlap
            if grounded:
                grounded_chunk_ids.add(cid)
            claims.append({"claim": quote or cid, "grounded": grounded, "chunk_id": cid})
    else:
        # Citation nélküli (legacy) út: szó szerinti idézet jelenléte a draftban.
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
        "verify_mode": verify_mode,
    }
