from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    case_id: str
    channel: str
    input_text_masked: str
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
    audit_refs: dict[str, Any]
