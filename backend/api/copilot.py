from __future__ import annotations

from fastapi import APIRouter

from agent.copilot.runner import run_copilot_turn
from backend.metadata import response_meta

from .contracts import CopilotChatRequest, CopilotChatResponse

router = APIRouter()


@router.post("/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(payload: CopilotChatRequest) -> dict:
    if not payload.message.strip():
        return {**response_meta(), "error": "message kotelezo"}
    result = run_copilot_turn(
        session_id=payload.session_id,
        message=payload.message,
        history=payload.history,
        customer_facing=payload.customer_facing,
    )
    return {**response_meta(), **result}
