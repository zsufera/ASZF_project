from __future__ import annotations

from typing import Any

from agent.copilot.session import CopilotSession
from backend import llm_tasks
from backend.history import get_history
from backend.services import classification_service, rag_service
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory


def classify(session: CopilotSession, **_: Any) -> dict[str, Any]:
    svc = classification_service.classify(session.message_masked)
    session.classification = svc
    session.record(
        step="classify",
        output={"category": svc["category"], "confidence": svc["confidence"]},
        mode=svc["mode"],
        summary=f'{svc["category"]} ({round(svc["confidence"] * 100)}%)',
    )
    return {"category": svc["category"], "confidence": svc["confidence"], "subtype": svc["subtype"]}


def knowledge_search(session: CopilotSession, *, category: str | None = None, **_: Any) -> dict[str, Any]:
    cat = category or (session.classification or {}).get("category") or "egyeb"
    result = rag_service.retrieve_for_case(
        text_masked=session.message_masked,
        category=cat,
        service_provider=None,
    )
    session.retrieval = result
    policy_items = result["policy_map"].get("policy_items", [])
    session.record(
        step="knowledge_search",
        output={"search_query": result["search_query"][:120], "result_count": result["result_count"]},
        mode=result["rewrite_mode"],
        counts={"results": result["result_count"], "policy_items": len(policy_items)},
        summary=f'{result["result_count"]} talalat',
    )
    return {
        "result_count": result["result_count"],
        "policy_item_count": len(policy_items),
        "sources": [
            {"ref": f"S{i + 1}", "idezet": item.get("idezet", "")[:160]}
            for i, item in enumerate(policy_items)
        ],
    }


def customer_context(session: CopilotSession, *, sender_email: str | None = None, **_: Any) -> dict[str, Any]:
    if not sender_email:
        session.record(step="customer_context", output={"history_loaded": False}, summary="nincs felado")
        return {"history_loaded": False, "is_repeated": False, "customer_count": 0}
    history = get_history(sender_email)
    candidates = MockCustomerDirectory().lookup_by_email(sender_email)
    session.customer = {"history": history, "candidates": candidates}
    session.record(
        step="customer_context",
        output={"history_loaded": True, "customer_count": len(candidates)},
        counts={"customers": len(candidates)},
        summary=f"{len(candidates)} ugyfel-jelolt",
    )
    return {
        "history_loaded": True,
        "is_repeated": bool(history.get("is_repeated")),
        "customer_count": len(candidates),
    }


def escalation_advice(session: CopilotSession, **_: Any) -> dict[str, Any]:
    classification = session.classification or {}
    policy_map = (session.retrieval or {}).get("policy_map", {})
    task = llm_tasks.suggest_escalation_task(
        confidence=float(classification.get("confidence", 0.0)),
        confidence_threshold=float(settings.confidence_threshold),
        is_repeated=bool(classification.get("is_repeated")),
        missing_mandatory=list(policy_map.get("missing_mandatory", [])),
        sla_expired=False,
        trigger_hits=[],
        text_masked=session.message_masked,
        category=str(classification.get("category", "egyeb")),
        policy_coverage=bool(policy_map.get("policy_items")),
    )
    session.escalation = task["result"]
    session.record(
        step="escalation_advice",
        output={"required": task["result"].get("required"), "reasons": task["result"].get("reasons", [])},
        mode=task["mode"],
        summary="eszkalacio szukseges" if task["result"].get("required") else "nem kell eszkalacio",
    )
    return {"required": bool(task["result"].get("required")), "reasons": task["result"].get("reasons", [])}


def draft_reply(session: CopilotSession, *, category: str | None = None, **_: Any) -> dict[str, Any]:
    cat = category or (session.classification or {}).get("category") or "egyeb"
    policy_map = (session.retrieval or {}).get("policy_map", {})
    task = llm_tasks.synthesize_answer_task(
        case_id=session.session_id,
        category=cat,
        channel="chat",
        output_mode="hitl",
        policy_map=policy_map,
        actions=[],
        input_text_masked=session.message_masked,
    )
    session.draft = task["result"]
    session.record(
        step="draft_reply",
        output={
            "format": task["result"].get("format"),
            "generation_mode": task["result"].get("generation_mode"),
            "source_count": len(task["result"].get("sources", [])),
        },
        mode=task["mode"],
        summary=f'draft ({task["result"].get("generation_mode")})',
    )
    return {
        "generation_mode": task["result"].get("generation_mode"),
        "body_masked": task["result"].get("body_masked", ""),
        "source_count": len(task["result"].get("sources", [])),
    }


def verify_grounding(session: CopilotSession, **_: Any) -> dict[str, Any]:
    draft = session.draft or {}
    chunks = (session.retrieval or {}).get("chunks", [])
    task = llm_tasks.verify_grounding_task(
        draft_body_masked=draft.get("body_masked", ""),
        chunks=chunks,
        mandatory_refs=[],
        citations=[str(c) for c in draft.get("citations", []) if c],
    )
    session.record(
        step="verify_grounding",
        output={"ungrounded_count": task["result"].get("ungrounded_count", 0)},
        mode=task["mode"],
        summary=f'{task["result"].get("ungrounded_count", 0)} nem megalapozott',
    )
    return {"ungrounded_count": task["result"].get("ungrounded_count", 0)}


SUBAGENTS = {
    "classify": classify,
    "knowledge_search": knowledge_search,
    "customer_context": customer_context,
    "escalation_advice": escalation_advice,
    "draft_reply": draft_reply,
    "verify_grounding": verify_grounding,
}
