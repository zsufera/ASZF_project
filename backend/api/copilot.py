from __future__ import annotations

from fastapi import APIRouter

from agent.copilot.runner import run_copilot_turn
from backend.copilot_session_service import handoff_copilot_session, list_copilot_sessions, record_copilot_turn
from backend.metadata import response_meta

from .contracts import CopilotChatRequest, CopilotChatResponse, CopilotHandoffRequest, CopilotTurnRecordRequest

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


@router.get("/copilot/sessions")
def copilot_sessions(username: str | None = None) -> dict:
    items = list_copilot_sessions(username=username)
    return {**response_meta(), "items": items, "count": len(items)}


@router.post("/copilot/sessions/turn")
def copilot_session_turn(payload: CopilotTurnRecordRequest) -> dict:
    result = record_copilot_turn(
        session_id=payload.session_id,
        role=payload.role,
        content=payload.content,
        username=payload.username,
        sources=payload.sources,
        timeline=payload.timeline,
    )
    return {**response_meta(), **result}


@router.post("/copilot/sessions/handoff")
def copilot_session_handoff(payload: CopilotHandoffRequest) -> dict:
    result = handoff_copilot_session(
        session_id=payload.session_id,
        username=payload.username,
        selected_turn_ids=payload.selected_turn_ids,
    )
    return {**response_meta(), **result}
