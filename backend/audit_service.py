from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.metadata import PROMPT_VERSION, load_manifest_summary
from config.settings import settings
from security.redaction import redact_payload


RETENTION_PATH = Path("config/retention.yaml")
REQUIRED_ITERATION_FIELDS = {
    "channel",
    "inbound_masked",
    "category",
    "confidence",
    "output_mode",
    "citations",
    "model_profile",
    "prompt_version",
    "aszf_version",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_case_db_id(case_code: str) -> int | None:
    try:
        with sqlite3.connect(settings.sqlite_path) as conn:
            row = conn.execute("SELECT id FROM cases WHERE case_code = ?", (case_code,)).fetchone()
    except sqlite3.OperationalError:
        return None
    return int(row[0]) if row else None


def record_audit_event(
    case_code: str,
    event_type: str,
    payload: dict[str, Any],
    actor_user_id: int | None = None,
) -> int:
    case_id = _get_case_db_id(case_code)
    if not case_id:
        raise ValueError("Ügy nem található")
    redacted = redact_payload(payload)
    with sqlite3.connect(settings.sqlite_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_events (case_id, event_type, actor_user_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (case_id, event_type, actor_user_id, json.dumps(redacted, ensure_ascii=False), _utc_now()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def record_iteration_audit(
    case_code: str,
    agent_result: dict[str, Any],
    *,
    inbound_masked: str,
    actor_user_id: int | None = None,
    history_case_ids: list[str] | None = None,
    postal_payload: dict[str, Any] | None = None,
) -> int:
    classification = agent_result.get("classification", {})
    draft = agent_result.get("draft", {})
    escalation = agent_result.get("escalation", {})
    retrieval = agent_result.get("retrieval", {})
    policy_map = agent_result.get("policy_map", {})
    audit_refs = agent_result.get("audit_refs", {})
    output_mode = agent_result.get("output_mode") or draft.get("output_mode") or "hitl"

    citations = []
    for chunk in retrieval.get("chunks", []):
        citations.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "paragrafus": chunk.get("paragrafus"),
                "dok_tipus": chunk.get("dok_tipus"),
            }
        )

    payload: dict[str, Any] = {
        "channel": agent_result.get("channel"),
        "inbound_masked": inbound_masked,
        "output_mode": output_mode,
        "category": classification.get("category"),
        "confidence": classification.get("confidence"),
        "escalation_required": escalation.get("required"),
        "escalation_reasons": escalation.get("reasons", []),
        "actions": agent_result.get("actions", []),
        "draft_subject_masked": draft.get("subject"),
        "draft_body_masked": draft.get("body_masked"),
        "citations": citations or draft.get("citations", []),
        "mandatory_refs": policy_map.get("mandatory_refs", []),
        "missing_mandatory": policy_map.get("missing_mandatory", []),
        "history_case_ids": history_case_ids or [],
        "selected_customer_id": agent_result.get("selected_customer_id"),
        "model_profile": audit_refs.get("model_profile") or agent_result.get("model_profile"),
        "prompt_version": audit_refs.get("prompt_version") or agent_result.get("prompt_version") or PROMPT_VERSION,
        "aszf_version": audit_refs.get("aszf_version") or agent_result.get("aszf_version"),
        "disclaimer_applied": draft.get("disclaimer_applied", False),
        "verify": agent_result.get("verify", {}),
        "postal": postal_payload,
    }
    event_id = record_audit_event(case_code, "case_iteration", payload, actor_user_id=actor_user_id)

    if output_mode == "automata":
        record_audit_event(
            case_code,
            "gdpr_art22_automated_decision",
            {
                "notice": load_retention_config().get("gdpr_art22_notice_hu"),
                "category": classification.get("category"),
                "confidence": classification.get("confidence"),
                "transparency_flag": True,
            },
            actor_user_id=actor_user_id,
        )
    return event_id


def record_pii_access(
    case_code: str,
    action: str,
    actor_user_id: int | None,
    role: str | None,
    details: dict[str, Any] | None = None,
) -> int:
    if not _get_case_db_id(case_code):
        return 0
    return record_audit_event(
        case_code,
        "pii_unmask_access",
        {"action": action, "role": role, **(details or {})},
        actor_user_id=actor_user_id,
    )


def list_audit_events(case_code: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if case_code:
        clauses.append("c.case_code = ?")
        params.append(case_code)
    params.append(limit)
    query = f"""
        SELECT a.id, c.case_code, a.event_type, a.actor_user_id, u.username,
               a.payload, a.created_at
        FROM audit_events a
        JOIN cases c ON c.id = a.case_id
        LEFT JOIN users u ON u.id = a.actor_user_id
        WHERE {' AND '.join(clauses)}
        ORDER BY a.created_at DESC
        LIMIT ?
    """
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = {}
        if row["payload"]:
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                payload = {"raw": row["payload"]}
        events.append(
            {
                "id": row["id"],
                "case_id": row["case_code"],
                "event_type": row["event_type"],
                "actor_user_id": row["actor_user_id"],
                "actor_username": row["username"],
                "payload": payload,
                "created_at": row["created_at"],
            }
        )
    return events


def build_case_audit_record(case_code: str) -> dict[str, Any] | None:
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return None

    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        inbound = conn.execute(
            """
            SELECT raw_text_masked, channel_payload
            FROM messages
            WHERE case_id = ? AND direction = 'inbound'
            ORDER BY created_at DESC LIMIT 1
            """,
            (case_id,),
        ).fetchone()
        drafts = conn.execute(
            """
            SELECT id, version_no, subject, body_masked, output_mode, disclaimer_applied,
                   citations, created_by_user_id, created_at
            FROM draft_versions WHERE case_id = ? ORDER BY version_no
            """,
            (case_id,),
        ).fetchall()
        feedback = conn.execute(
            """
            SELECT payload, created_at FROM audit_events
            WHERE case_id = ? AND event_type = 'ui_feedback'
            ORDER BY created_at DESC LIMIT 1
            """,
            (case_id,),
        ).fetchone()

    events = list_audit_events(case_code=case_code, limit=200)
    iterations = [event for event in events if event["event_type"] == "case_iteration"]
    manifest = load_manifest_summary()

    latest_iteration = iterations[0]["payload"] if iterations else {}
    draft_versions = [
        {
            "id": row["id"],
            "version_no": row["version_no"],
            "subject_masked": row["subject"],
            "body_masked": row["body_masked"],
            "output_mode": row["output_mode"],
            "disclaimer_applied": bool(row["disclaimer_applied"]),
            "citations": json.loads(row["citations"]) if row["citations"] else [],
            "created_by_user_id": row["created_by_user_id"],
            "created_at": row["created_at"],
        }
        for row in drafts
    ]

    inbound_payload = {}
    if inbound and inbound["channel_payload"]:
        try:
            inbound_payload = json.loads(inbound["channel_payload"])
        except json.JSONDecodeError:
            inbound_payload = {}

    return {
        "case_id": case_code,
        "channel": case["channel"],
        "status": case["status"],
        "priority": case["priority"],
        "confidence": case["confidence"],
        "escalated": bool(case["escalated"]),
        "escalation_reasons": json.loads(case["escalation_reasons"]) if case["escalation_reasons"] else [],
        "sender_email_masked": case["sender_email_masked"],
        "selected_customer_id": case["selected_customer_id"],
        "service_provider": case["service_provider"],
        "inbound_masked": inbound["raw_text_masked"] if inbound else "",
        "inbound_subject": inbound_payload.get("subject"),
        "iterations": iterations,
        "draft_versions": draft_versions,
        "latest_iteration": latest_iteration,
        "ui_feedback": json.loads(feedback["payload"]) if feedback and feedback["payload"] else None,
        "events": events,
        "audit_meta": {
            "prompt_version": PROMPT_VERSION,
            "aszf_version": manifest.get("aszf_version"),
        },
    }


def check_audit_completeness(case_code: str) -> dict[str, Any]:
    record = build_case_audit_record(case_code)
    if not record:
        return {"case_id": case_code, "complete": False, "missing": ["case_not_found"]}

    missing: list[str] = []
    latest = record.get("latest_iteration") or {}
    for field in REQUIRED_ITERATION_FIELDS:
        if field not in latest or latest.get(field) in (None, "", []):
            missing.append(field)

    if record["status"] == "lezarva":
        approved = any(event["event_type"] == "draft_approved_mock_send" for event in record["events"])
        if not approved:
            missing.append("approval_event")
        if not record.get("draft_versions"):
            missing.append("draft_version")

    automata_iterations = [
        event for event in record["events"]
        if event["event_type"] == "case_iteration" and event["payload"].get("output_mode") == "automata"
    ]
    if automata_iterations:
        art22 = any(event["event_type"] == "gdpr_art22_automated_decision" for event in record["events"])
        if not art22:
            missing.append("gdpr_art22_event")
        disclaimer_ok = any(
            event["payload"].get("disclaimer_applied") for event in automata_iterations
        )
        if not disclaimer_ok:
            missing.append("disclaimer_applied")

    return {
        "case_id": case_code,
        "complete": not missing,
        "missing": missing,
        "required_fields": sorted(REQUIRED_ITERATION_FIELDS),
    }


def load_retention_config(path: Path = RETENTION_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
