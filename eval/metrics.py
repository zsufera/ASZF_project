from __future__ import annotations

from typing import Any


def expected_escalation(payload: dict[str, Any], classification: dict[str, Any]) -> bool:
    if payload.get("varhato_eszkalacio"):
        return True
    edge = payload.get("edge_case")
    if edge in {"hatokoron_kivuli", "egyedi_szerzodes_gyanu", "prompt_injection", "ismetlodo_panasz"}:
        return True
    if edge == "nem_panasz":
        return False
    return float(classification.get("confidence", 1.0)) < 0.75


def compute_faithfulness(verify_result: dict[str, Any]) -> float:
    claims = verify_result.get("claims") or []
    if not claims:
        return 1.0 if verify_result.get("ungrounded_count", 0) == 0 else 0.0
    grounded = sum(1 for claim in claims if claim.get("grounded"))
    return round(grounded / len(claims), 3)


def compute_citation_support(draft: dict[str, Any], chunks: list[dict[str, Any]]) -> bool:
    citations = set(draft.get("citations") or [])
    if citations:
        chunk_ids = {str(chunk.get("chunk_id")) for chunk in chunks if chunk.get("chunk_id")}
        return bool(citations & chunk_ids)
    body = draft.get("body_masked", "")
    for chunk in chunks:
        quote = str(chunk.get("quote", "")).strip()
        if quote and quote[:40] in body:
            return True
    return False


def compute_retrieval_consistency(query: str, chunks: list[dict[str, Any]]) -> bool:
    if not chunks:
        return False
    query_terms = {term for term in query.lower().split() if len(term) > 4}
    if not query_terms:
        return True
    for chunk in chunks:
        quote = str(chunk.get("quote", "")).lower()
        if any(term in quote for term in query_terms):
            return True
    return bool(chunks)


def compute_coverage(
    chunks: list[dict[str, Any]],
    draft: dict[str, Any],
    escalation_required: bool,
    edge_case: str | None,
) -> bool:
    if edge_case == "hatokoron_kivuli":
        return escalation_required
    if edge_case == "nem_panasz":
        return bool(draft.get("body_masked"))
    return bool(chunks) and bool(draft.get("body_masked"))


def compute_out_of_scope_violation(
    edge_case: str | None,
    escalation_required: bool,
    draft: dict[str, Any],
) -> bool:
    if edge_case != "hatokoron_kivuli":
        return False
    has_substantive_draft = len(draft.get("body_masked", "")) > 120
    return has_substantive_draft and not escalation_required


def kpi_status(value: float, target: float, higher_is_better: bool = True) -> str:
    if higher_is_better:
        if value >= target:
            return "green"
        if value >= target * 0.9:
            return "yellow"
        return "red"
    if value <= target:
        return "green"
    if value <= target * 1.1:
        return "yellow"
    return "red"
