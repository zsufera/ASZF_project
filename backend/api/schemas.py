from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    case_id: str
    message_text_masked: str
    history_summary_masked: str | None = None


class RetrieveRequest(BaseModel):
    case_id: str
    query_masked: str
    service_provider: str | None = None
    customer_id: str | None = None
    limit: int = 5


class PolicyMapRequest(BaseModel):
    case_id: str
    category: str
    chunks: list[dict]


class DraftRequest(BaseModel):
    case_id: str
    category: str
    output_mode: str
    policy_map: dict
    actions: list[dict] = Field(default_factory=list)
    channel: str = "email"
    input_text_masked: str | None = None


class VerifyRequest(BaseModel):
    case_id: str
    draft_body_masked: str
    chunks: list[dict]
    mandatory_refs: list[str]


class MaskRequest(BaseModel):
    case_id: str
    text: str


class UnmaskRequest(BaseModel):
    case_id: str
    draft_version_id: int | None = None
    subject_masked: str | None = None
    body_masked: str | None = None
    username: str | None = None
    role: str | None = None


class ReindexRequest(BaseModel):
    force: bool = False


class EvalRequest(BaseModel):
    limit: int = 10
    category: str | None = None
    service_provider: str | None = None
    include_edge: bool = True
    save_report: bool = True


class EvalBaselineRequest(BaseModel):
    run_id: str


class EvalHumanScoreRequest(BaseModel):
    run_id: str
    email_id: str
    score: int = Field(ge=1, le=5)


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


class LoginRequest(BaseModel):
    username: str
    password: str


class InboxQuery(BaseModel):
    category: str | None = None
    priority: str | None = None
    status: str | None = None
    channel: str | None = None
    search: str | None = None
    sort_by: str = "priority"


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


class FeedbackRequest(BaseModel):
    case_id: str
    rating: str
    wrong_source: bool = False
    username: str | None = None


class SeedRequest(BaseModel):
    force: bool = False


class StatusTransitionRequest(BaseModel):
    case_id: str
    target_status: str
    username: str | None = None
    role: str | None = None


class PurgeRequest(BaseModel):
    dry_run: bool = True
    username: str | None = None
    role: str | None = None


class AcceptanceRequest(BaseModel):
    eval_limit: int = 10
    include_edge: bool = True
    run_demo: bool = True


class DemoRunRequest(BaseModel):
    save_report: bool = True
