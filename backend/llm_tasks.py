from __future__ import annotations

import logging
from typing import Any

from backend.classify import classify_message
from backend.draft import synthesize_answer
from backend.escalation import decide_escalation, llm_escalation_suggestion, merge_escalation
from backend.query_rewrite import rewrite_query
from backend.verify import verify_draft

logger = logging.getLogger(__name__)


def _ok(mode: str, result: Any) -> dict[str, Any]:
    return {"mode": mode, "result": result, "error": None}


def _fail(error: str, fallback: Any, mode: str) -> dict[str, Any]:
    return {"mode": mode, "result": fallback, "error": error}


def classify_message_task(
    message_text_masked: str, history_summary_masked: str | None = None
) -> dict[str, Any]:
    try:
        result = classify_message(message_text_masked, history_summary_masked)
        return _ok(result.get("classify_mode", "rule"), result)
    except Exception as exc:
        logger.exception("classify_message_task failed")
        return _fail(str(exc), {"category": "egyeb", "confidence": 0.0, "candidates": []}, "rule")


def rewrite_query_task(text: str, category: str) -> dict[str, Any]:
    try:
        query = rewrite_query(text, category)
        return _ok("llm" if query != text else "rule", query)
    except Exception as exc:
        logger.exception("rewrite_query_task failed")
        return _fail(str(exc), text, "rule")


def suggest_escalation_task(
    *,
    confidence: float,
    confidence_threshold: float,
    is_repeated: bool,
    missing_mandatory: list[str],
    sla_expired: bool,
    trigger_hits: list[str],
    text_masked: str,
    category: str,
    policy_coverage: bool,
) -> dict[str, Any]:
    try:
        rule = decide_escalation(
            confidence=confidence,
            confidence_threshold=confidence_threshold,
            is_repeated=is_repeated,
            missing_mandatory=missing_mandatory,
            sla_expired=sla_expired,
            trigger_hits=trigger_hits,
        )
        suggestion = llm_escalation_suggestion(
            text_masked=text_masked,
            category=category,
            confidence=confidence,
            policy_coverage=policy_coverage,
        )
        merged = merge_escalation(rule, suggestion)
        mode = "rule+llm" if suggestion.get("suggested") else "rule"
        return _ok(mode, merged)
    except Exception as exc:
        logger.exception("suggest_escalation_task failed")
        return _fail(str(exc), {"required": False, "reasons": []}, "rule")


def synthesize_answer_task(**kwargs: Any) -> dict[str, Any]:
    try:
        result = synthesize_answer(**kwargs)
        return _ok(result.get("generation_mode", "template"), result)
    except Exception as exc:
        logger.exception("synthesize_answer_task failed")
        return _fail(str(exc), {"body_masked": "", "generation_mode": "insufficient"}, "insufficient")


def verify_grounding_task(
    *,
    draft_body_masked: str,
    chunks: list[dict[str, Any]],
    mandatory_refs: list[str],
    citations: list[str] | None = None,
) -> dict[str, Any]:
    try:
        result = verify_draft(
            draft_body_masked=draft_body_masked,
            chunks=chunks,
            mandatory_refs=mandatory_refs,
            citations=citations,
        )
        return _ok(result.get("verify_mode", "heuristic"), result)
    except Exception as exc:
        logger.exception("verify_grounding_task failed")
        return _fail(str(exc), {"ungrounded_count": 0, "claims": []}, "heuristic")
