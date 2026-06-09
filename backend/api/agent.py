from __future__ import annotations

from fastapi import APIRouter

from agent.runner import run_agent
from backend.metadata import response_meta

from .contracts import AgentRunRequest, AgentRunResponse


router = APIRouter()


@router.post("/agent/run", response_model=AgentRunResponse)
def agent_run(payload: AgentRunRequest) -> dict:
    if not payload.input_text and not payload.input_text_masked:
        return {**response_meta(), "error": "input_text vagy input_text_masked kotelezo"}
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
