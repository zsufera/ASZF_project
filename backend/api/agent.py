from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.runner import run_agent
from backend.metadata import response_meta
from backend.sse import sse_event, stream_timeline_worker

from .contracts import AgentRunRequest, AgentRunResponse


router = APIRouter()


def _run_agent_payload(payload: AgentRunRequest, on_timeline_step: Callable[[dict], None] | None = None) -> dict:
    return run_agent(
        case_id=payload.case_id,
        channel=payload.channel,
        input_text=payload.input_text,
        input_text_masked=payload.input_text_masked,
        sender_email=payload.sender_email,
        service_provider=payload.service_provider,
        output_mode=payload.output_mode,
        selected_customer_id=payload.selected_customer_id,
        history_summary_masked=payload.history_summary_masked,
        sla_expired=payload.sla_expired,
        on_timeline_step=on_timeline_step,
    )


@router.post("/agent/run", response_model=AgentRunResponse)
def agent_run(payload: AgentRunRequest) -> dict:
    if not payload.input_text and not payload.input_text_masked:
        return {**response_meta(), "error": "input_text vagy input_text_masked kotelezo"}
    return _run_agent_payload(payload)


@router.post("/agent/run/stream")
def agent_run_stream(payload: AgentRunRequest) -> StreamingResponse:
    if not payload.input_text and not payload.input_text_masked:
        return StreamingResponse(
            iter([sse_event("error", {"error": "input_text vagy input_text_masked kotelezo"})]),
            media_type="text/event-stream",
        )

    events = stream_timeline_worker(
        start={"case_id": payload.case_id},
        run=lambda emit: _run_agent_payload(payload, on_timeline_step=emit),
        complete_meta=response_meta(),
    )

    return StreamingResponse(events, media_type="text/event-stream")
