from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.copilot.runner import run_copilot_turn
from backend.copilot_session_service import handoff_copilot_session, list_copilot_sessions, record_copilot_turn
from backend.metadata import response_meta
from backend.sse import sse_event, stream_timeline_worker

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


@router.post("/copilot/chat/stream")
def copilot_chat_stream(payload: CopilotChatRequest) -> StreamingResponse:
    if not payload.message.strip():
        return StreamingResponse(
            iter([sse_event("error", {"error": "message kotelezo"})]),
            media_type="text/event-stream",
        )

    def run(emit_step):
        return {
            **response_meta(),
            **run_copilot_turn(
                session_id=payload.session_id,
                message=payload.message,
                history=payload.history,
                customer_facing=payload.customer_facing,
                on_timeline_step=emit_step,
            ),
        }

    events = stream_timeline_worker(start={"session_id": payload.session_id}, run=run)
    return StreamingResponse(events, media_type="text/event-stream")


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
