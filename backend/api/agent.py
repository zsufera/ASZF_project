from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.runner import run_agent
from backend.metadata import response_meta

from .contracts import AgentRunRequest, AgentRunResponse


router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _run_agent_payload(payload: AgentRunRequest) -> dict:
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
    )


@router.post("/agent/run", response_model=AgentRunResponse)
def agent_run(payload: AgentRunRequest) -> dict:
    if not payload.input_text and not payload.input_text_masked:
        return {**response_meta(), "error": "input_text vagy input_text_masked kotelezo"}
    return _run_agent_payload(payload)


@router.post("/agent/run/stream")
def agent_run_stream(payload: AgentRunRequest) -> StreamingResponse:
    def events() -> Iterator[str]:
        if not payload.input_text and not payload.input_text_masked:
            yield _sse("error", {"error": "input_text vagy input_text_masked kotelezo"})
            return

        yield _sse("start", {"case_id": payload.case_id})
        result = _run_agent_payload(payload)
        for idx, step in enumerate(result.get("timeline", []), start=1):
            yield _sse("step", {"index": idx, "step": step})
        yield _sse("complete", {**response_meta(), **result})

    return StreamingResponse(events(), media_type="text/event-stream")
