from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from agent.graph import compiled_agent_graph
from agent.state import AgentState
from backend.metadata import response_meta
from backend.tracing_service import trace_event
from config.settings import settings


def build_initial_state(
    case_id: str,
    channel: str,
    input_text: str | None = None,
    input_text_masked: str | None = None,
    sender_email: str | None = None,
    sender_email_key: str | None = None,
    service_provider: str | None = None,
    output_mode: str = "hitl",
    selected_customer_id: str | None = None,
    history_summary_masked: str | None = None,
    customer_candidates: list[dict[str, Any]] | None = None,
    sla_expired: bool = False,
) -> AgentState:
    return {
        "case_id": case_id,
        "channel": channel,
        "input_text": input_text,
        "input_text_masked": input_text_masked,
        "sender_email": sender_email,
        "sender_email_key": sender_email_key,
        "service_provider": service_provider,
        "output_mode": output_mode,
        "selected_customer_id": selected_customer_id,
        "history_summary_masked": history_summary_masked,
        "customer_candidates": customer_candidates or [],
        "sla_expired": sla_expired,
        "timeline": [],
    }


def persist_agent_run(case_id: str, state: AgentState) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    audit_refs = state.get("audit_refs", {})
    snapshot = {
        "lang_type": state.get("lang_type"),
        "classification": state.get("classification"),
        "priority": state.get("priority"),
        "retrieval": state.get("retrieval"),
        "policy_map": state.get("policy_map"),
        "escalation": state.get("escalation"),
        "actions": state.get("actions"),
        "draft": state.get("draft"),
        "verify": state.get("verify"),
        "timeline": state.get("timeline"),
    }
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_runs (case_id, prompt_version_bundle, model_profile, state_snapshot, started_at, ended_at)
            VALUES (
                (SELECT id FROM cases WHERE case_code = ? LIMIT 1),
                ?, ?, ?, ?, ?
            )
            """,
            (
                case_id,
                audit_refs.get("prompt_version"),
                audit_refs.get("model_profile"),
                json.dumps(snapshot, ensure_ascii=False),
                started_at,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def run_agent(
    case_id: str,
    channel: str = "email",
    input_text: str | None = None,
    input_text_masked: str | None = None,
    sender_email: str | None = None,
    sender_email_key: str | None = None,
    service_provider: str | None = None,
    output_mode: str = "hitl",
    selected_customer_id: str | None = None,
    history_summary_masked: str | None = None,
    customer_candidates: list[dict[str, Any]] | None = None,
    sla_expired: bool = False,
    persist: bool = False,
) -> dict[str, Any]:
    initial = build_initial_state(
        case_id=case_id,
        channel=channel,
        input_text=input_text,
        input_text_masked=input_text_masked,
        sender_email=sender_email,
        sender_email_key=sender_email_key,
        service_provider=service_provider,
        output_mode=output_mode,
        selected_customer_id=selected_customer_id,
        history_summary_masked=history_summary_masked,
        customer_candidates=customer_candidates,
        sla_expired=sla_expired,
    )
    started = time.perf_counter()
    final_state = compiled_agent_graph.invoke(initial)
    duration_ms = int((time.perf_counter() - started) * 1000)
    if persist:
        try:
            persist_agent_run(case_id, final_state)
        except sqlite3.Error:
            pass

    trace_event(
        "agent_run",
        {
            "channel": channel,
            "classification": final_state.get("classification", {}).get("category"),
            "escalated": final_state.get("escalation", {}).get("required"),
            "draft_format": final_state.get("draft", {}).get("format"),
            "timeline_steps": len(final_state.get("timeline", [])),
        },
        case_id=case_id,
        duration_ms=duration_ms,
    )

    return {
        **response_meta(),
        "case_id": case_id,
        "channel": channel,
        "lang_type": final_state.get("lang_type"),
        "classification": final_state.get("classification"),
        "priority": final_state.get("priority"),
        "retrieval": final_state.get("retrieval"),
        "policy_map": final_state.get("policy_map"),
        "escalation": final_state.get("escalation"),
        "actions": final_state.get("actions"),
        "draft": final_state.get("draft"),
        "verify": final_state.get("verify"),
        "draft_preview_unmasked": final_state.get("draft_preview_unmasked"),
        "audit_refs": final_state.get("audit_refs"),
        "timeline": final_state.get("timeline", []),
        "customer_candidates": final_state.get("customer_candidates", []),
    }
