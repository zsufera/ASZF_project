from __future__ import annotations

from typing import Any


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
