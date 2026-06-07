from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    case_id: str
    channel: str
    input_text: str
    input_text_masked: str
    sender_email: str | None
    service_provider: str | None
    output_mode: str
    sla_expired: bool
    history_summary_masked: str | None
    customer_candidates: list[dict[str, Any]]
    selected_customer_id: str | None
    lang_type: dict[str, Any]
    classification: dict[str, Any]
    priority: dict[str, Any]
    retrieval: dict[str, Any]
    policy_map: dict[str, Any]
    escalation: dict[str, Any]
    actions: list[dict[str, Any]]
    draft: dict[str, Any]
    verify: dict[str, Any]
    draft_preview_unmasked: dict[str, Any]
    audit_refs: dict[str, Any]
    timeline: list[dict[str, Any]]
