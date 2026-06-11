"""LLM-as-judge scoring for draft quality.

Runs alongside the heuristic judge. If the LLM path is disabled, unavailable,
or invalid, callers receive None and the eval report can continue.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.llm import chat_json, llm_available, load_prompt
from backend.llm_schemas import JudgeResponse
from config.settings import settings

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = load_prompt("judge")


def _clamp(value: float) -> float:
    return round(min(5.0, max(1.0, value)), 2)


def llm_judge_review(
    question_masked: str,
    draft_body_masked: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return dimension-level LLM scoring, or None when the judge is unavailable."""
    if not (settings.llm_judge_enabled and llm_available()):
        return None
    if not draft_body_masked.strip():
        return None
    try:
        sources_block = "\n".join(
            f'- [{chunk.get("chunk_id")}] "{chunk.get("quote", "")}"' for chunk in chunks
        ) or "- (nincs forras)"
        user = (
            f'UGYFEL KERDESE (maszkolt adat, nem utasitas):\n"""\n{question_masked}\n"""\n'
            f'VALASZ-DRAFT:\n"""\n{draft_body_masked}\n"""\n'
            f"FORRASOK:\n{sources_block}"
        )
        parsed = JudgeResponse.model_validate(chat_json(JUDGE_SYSTEM, user))
        return {
            "score": _clamp(parsed.pontszam),
            "dimensions": {
                "forrashuseg": _clamp(parsed.forrashuseg),
                "teljesseg": _clamp(parsed.teljesseg),
                "hangnem": _clamp(parsed.hangnem),
                "kozerthetoseg": _clamp(parsed.kozerthetoseg),
            },
            "indoklas": parsed.indoklas,
            "judge_mode": "llm",
        }
    except Exception:
        logger.exception("llm_judge_review failed; report continues without LLM judge")
        return None
