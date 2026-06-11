from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlexibleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class AgentRunRequest(BaseModel):
    case_id: str
    channel: str = "email"
    input_text: str | None = None
    input_text_masked: str | None = None
    sender_email: str | None = None
    service_provider: str | None = None
    output_mode: str = "hitl"
    selected_customer_id: str | None = None
    history_summary_masked: str | None = None
    sla_expired: bool = False


class CaseProcessRequest(BaseModel):
    case_id: str
    output_mode: str = "hitl"
    username: str | None = None
    selected_customer_id: str | None = None
    service_provider: str | None = None
    input_text_masked: str | None = None
    sla_expired: bool = False


class CaseCreateRequest(BaseModel):
    channel: str = "email"
    input_text: str
    sender_email: str | None = None
    service_provider: str | None = None


class DraftSaveRequest(BaseModel):
    case_id: str
    subject: str
    body_masked: str
    output_mode: str = "hitl"
    citations: list[str] = Field(default_factory=list)
    username: str | None = None


class DraftApproveRequest(BaseModel):
    case_id: str
    draft_version_id: int | None = None
    subject_masked: str | None = None
    body_masked: str | None = None
    username: str | None = None
    role: str | None = None


class FeedbackRequest(BaseModel):
    case_id: str
    rating: str
    wrong_source: bool = False
    reason: str | None = None
    username: str | None = None


class SeedRequest(BaseModel):
    force: bool = False


class StatusTransitionRequest(BaseModel):
    case_id: str
    target_status: str
    username: str | None = None
    role: str | None = None


class CaseClaimRequest(BaseModel):
    case_id: str
    username: str | None = None


class CaseAssignRequest(BaseModel):
    case_id: str
    assignee_username: str
    username: str | None = None


class CaseReleaseRequest(BaseModel):
    case_id: str
    username: str | None = None


class InboxResponse(FlexibleResponse):
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class CaseDetailResponse(FlexibleResponse):
    case_id: str | None = None
    error: str | None = None


class CaseProcessResponse(FlexibleResponse):
    case_id: str | None = None
    status: str | None = None
    error: str | None = None


class DraftApproveResponse(FlexibleResponse):
    case_id: str | None = None
    status: str | None = None
    mock_sent: bool | None = None
    subject_unmasked: str | None = None
    body_unmasked: str | None = None
    error: str | None = None


class HistoryResponse(FlexibleResponse):
    items: list[dict[str, Any]] = Field(default_factory=list)
    is_repeated: bool = False


class AgentRunResponse(FlexibleResponse):
    case_id: str | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class CopilotChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    customer_facing: bool = False


class CopilotTurnRecordRequest(BaseModel):
    session_id: str
    role: str
    content: str
    username: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class CopilotHandoffRequest(BaseModel):
    session_id: str
    username: str | None = None
    selected_turn_ids: list[int] = Field(default_factory=list)


class CopilotChatResponse(FlexibleResponse):
    reply: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    draft: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    orchestrator_mode: str | None = None
    error: str | None = None
