from __future__ import annotations

import logging
from typing import Any

from backend.llm import chat_json, llm_available, load_prompt
from backend.llm_schemas import EscalationResponse

logger = logging.getLogger(__name__)

ESCALATION_SYSTEM = load_prompt("escalation")


def decide_escalation(
    confidence: float,
    confidence_threshold: float,
    is_repeated: bool,
    missing_mandatory: list[str],
    sla_expired: bool,
    trigger_hits: list[str],
) -> dict[str, Any]:
    reasons: list[str] = []

    if confidence < confidence_threshold:
        reasons.append("alacsony_konfidencia")
    if missing_mandatory:
        reasons.append("hianyzo_kotelezo_hivatkozas")
    if is_repeated:
        reasons.append("ismetlod_panasz")
    if sla_expired:
        reasons.append("sla_lejart")
    reasons.extend(trigger_hits)

    return {"required": bool(reasons), "reasons": reasons}


def llm_escalation_suggestion(
    text_masked: str,
    category: str,
    confidence: float,
    policy_coverage: bool,
) -> dict[str, Any]:
    if not llm_available():
        return {"suggested": False, "okok": []}
    try:
        user = (
            f"Kategória/konfidencia: {category} / {confidence}\n"
            f"Szabályzat-térkép lefedi a kérdést?: {policy_coverage}\n"
            f'Maszkolt üzenet:\n"""\n{text_masked}\n"""'
        )
        parsed = EscalationResponse.model_validate(chat_json(ESCALATION_SYSTEM, user))
        return {"suggested": parsed.eszkalacio, "okok": parsed.okok}
    except Exception:
        logger.exception("llm_escalation_suggestion failed; ignoring LLM suggestion")
        return {"suggested": False, "okok": []}


def merge_escalation(rule_result: dict[str, Any], suggestion: dict[str, Any]) -> dict[str, Any]:
    if not suggestion.get("suggested"):
        return {**rule_result, "llm_reasoning": None}
    reasons = sorted(
        set(list(rule_result.get("reasons", [])) + list(suggestion.get("okok", [])) + ["llm_javaslat"])
    )
    reasoning = "; ".join(suggestion.get("okok", [])) or "LLM eszkalációt javasolt."
    return {**rule_result, "required": True, "reasons": reasons, "llm_reasoning": reasoning}
