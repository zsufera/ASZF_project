from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.copilot import orchestrator
from agent.copilot.session import CopilotSession
from backend.draft import strip_source_markers
from backend.masking import mask_text, unmask_text


def run_copilot_turn(
    session_id: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    customer_facing: bool = False,
    on_timeline_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    masked = mask_text(session_id, message)
    session = CopilotSession(
        session_id=session_id,
        message_masked=masked["masked_text"],
        history=history or [],
        on_timeline_step=on_timeline_step,
    )
    result = orchestrator.run(session)
    reply_unmasked = unmask_text(session_id, result["reply_masked"])
    reply = strip_source_markers(reply_unmasked) if customer_facing else reply_unmasked
    return {
        "reply": reply,
        "sources": result["sources"],
        "draft": result["draft"],
        "escalation": result["escalation"],
        "timeline": result["timeline"],
        "orchestrator_mode": result["orchestrator_mode"],
    }
