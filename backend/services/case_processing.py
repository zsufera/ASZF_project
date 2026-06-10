"""Case processing functions extracted from case_service.

Contains: process_case, save_draft_version, approve_draft.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from agent.runner import run_agent
from backend.audit_service import record_audit_event, record_iteration_audit, record_pii_access
from backend.case_service import (
    _clean_outbound_text,
    _get_case_db_id,
    _utc_now,
    get_case_detail,
)
from backend.draft import ensure_disclaimer
from backend.history import get_history
from backend.masking import unmask_text
from backend.workflow import validate_transition
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory
from security.rbac import require_permission


def process_case(
    case_code: str,
    output_mode: str = "hitl",
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    selected_customer_id: str | None = None,
    service_provider: str | None = None,
    input_text_masked: str | None = None,
    sla_expired: bool = False,
) -> dict[str, Any]:
    detail = get_case_detail(case_code)
    if not detail:
        return {"error": "Ügy nem található", "case_id": case_code}

    sender = detail.get("sender_email_masked")
    sender_key = detail.get("sender_email_key")
    provider = service_provider or detail.get("service_provider")
    text = input_text_masked or detail.get("inbound_text_masked") or ""

    if output_mode == "automata":
        require_permission(actor_role or "ui", "run_automata_mode")

    result = run_agent(
        case_id=case_code,
        channel=detail["channel"],
        input_text_masked=text,
        sender_email=sender,
        sender_email_key=sender_key,
        service_provider=provider,
        output_mode=output_mode,
        selected_customer_id=selected_customer_id,
        sla_expired=sla_expired,
        persist=True,
    )
    result["channel"] = detail["channel"]
    result["output_mode"] = output_mode
    draft = result.get("draft", {})
    if draft.get("body_masked"):
        body_with_disclaimer, disclaimer_applied = ensure_disclaimer(draft["body_masked"], output_mode)
        draft["body_masked"] = body_with_disclaimer
        draft["disclaimer_applied"] = disclaimer_applied
        result["draft"] = draft

    history_case_ids: list[str] = []
    if sender:
        history = get_history(sender, sender_email_key=sender_key)
        history_case_ids = [item["case_id"] for item in history.get("items", []) if item.get("case_id") != case_code]

    classification = result.get("classification", {})
    priority = result.get("priority", {})
    escalation = result.get("escalation", {})
    category = classification.get("category")
    status = "eszkalalva" if escalation.get("required") else "folyamatban"
    version_no: int | None = None

    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            UPDATE cases
            SET status = ?, priority = ?, confidence = ?, escalated = ?,
                escalation_reasons = ?, service_provider = COALESCE(?, service_provider),
                selected_customer_id = COALESCE(?, selected_customer_id), updated_at = ?
            WHERE case_code = ?
            """,
            (
                status,
                priority.get("value", "normal"),
                classification.get("confidence"),
                1 if escalation.get("required") else 0,
                json.dumps(escalation.get("reasons", []), ensure_ascii=False),
                provider,
                selected_customer_id,
                _utc_now(),
                case_code,
            ),
        )
        case_id = _get_case_db_id(case_code)
        if case_id:
            payload = json.dumps(
                {
                    "subject": detail.get("subject"),
                    "category": category,
                    "expected_category": detail.get("category"),
                },
                ensure_ascii=False,
            )
            conn.execute(
                """
                UPDATE messages
                SET channel_payload = ?, message_type = ?
                WHERE case_id = ? AND direction = 'inbound'
                """,
                (
                    payload,
                    "nem_panasz" if classification.get("subtype") == "nem_panasz" else "panasz",
                    case_id,
                ),
            )
            conn.execute("DELETE FROM customer_candidates WHERE case_id = ?", (case_id,))
            for candidate in result.get("customer_candidates") or MockCustomerDirectory().lookup_by_email(sender or ""):
                conn.execute(
                    """
                    INSERT INTO customer_candidates
                    (case_id, source, customer_id, customer_name, link_url, selected)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        candidate.get("source", "mock"),
                        candidate["customer_id"],
                        candidate["customer_name"],
                        candidate.get("link_url"),
                        1 if candidate["customer_id"] == selected_customer_id else 0,
                    ),
                )
            draft = result.get("draft", {})
            verify = result.get("verify", {})
            version_no = conn.execute(
                "SELECT COALESCE(MAX(version_no), 0) + 1 FROM draft_versions WHERE case_id = ?",
                (case_id,),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO draft_versions
                (case_id, version_no, subject, body_masked, output_mode, disclaimer_applied,
                 citations, verify_result, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    version_no,
                    draft.get("subject"),
                    draft.get("body_masked"),
                    "automata" if output_mode == "automata" else "hitl",
                    1 if draft.get("disclaimer_applied") else 0,
                    json.dumps(draft.get("citations", []), ensure_ascii=False),
                    json.dumps(verify, ensure_ascii=False),
                    actor_user_id,
                ),
            )
        conn.commit()

    record_iteration_audit(
        case_code,
        result,
        inbound_masked=text,
        actor_user_id=actor_user_id,
        history_case_ids=history_case_ids,
    )

    return {
        "case_id": case_code,
        "status": status,
        "draft_version_no": version_no if case_id else None,
        **result,
    }


def save_draft_version(
    case_code: str,
    subject: str,
    body_masked: str,
    output_mode: str,
    citations: list[str],
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ügy nem található"}
    if output_mode == "automata":
        require_permission(actor_role, "run_automata_mode")
    body_masked, disclaimer_applied = ensure_disclaimer(body_masked, output_mode)
    with sqlite3.connect(settings.sqlite_path) as conn:
        version_no = conn.execute(
            "SELECT COALESCE(MAX(version_no), 0) + 1 FROM draft_versions WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO draft_versions
            (case_id, version_no, subject, body_masked, output_mode, disclaimer_applied, citations, created_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                version_no,
                subject,
                body_masked,
                "automata" if output_mode == "automata" else "hitl",
                1 if disclaimer_applied else 0,
                json.dumps(citations, ensure_ascii=False),
                actor_user_id,
            ),
        )
        current_status = conn.execute("SELECT status FROM cases WHERE id = ?", (case_id,)).fetchone()[0]
        validate_transition(current_status, "jovahagyasra_var")
        conn.execute(
            "UPDATE cases SET status = 'jovahagyasra_var', updated_at = ? WHERE id = ?",
            (_utc_now(), case_id),
        )
        draft_version_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    record_audit_event(
        case_code,
        "draft_saved",
        {
            "version_no": version_no,
            "output_mode": output_mode,
            "disclaimer_applied": disclaimer_applied,
            "citation_count": len(citations),
        },
        actor_user_id=actor_user_id,
    )
    return {"case_id": case_code, "version_no": version_no, "draft_version_id": draft_version_id}


def approve_draft(
    case_code: str,
    draft_version_id: int | None = None,
    subject_masked: str | None = None,
    body_masked: str | None = None,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    require_permission(actor_role, "approve_draft")
    require_permission(actor_role, "unmask")
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ügy nem található"}

    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        if draft_version_id:
            row = conn.execute(
                "SELECT subject, body_masked, verify_result FROM draft_versions WHERE id = ? AND case_id = ?",
                (draft_version_id, case_id),
            ).fetchone()
            if not row:
                return {"error": "Draft verzió nem található", "case_id": case_code}
            verify_result = json.loads(row["verify_result"]) if row["verify_result"] else {}
            if (
                verify_result.get("warning")
                or verify_result.get("ungrounded_count", 0)
                or verify_result.get("missing_mandatory")
            ):
                return {
                    "error": "A draft nem hagyható jóvá, mert a forrásoltsági ellenőrzés hibát jelzett.",
                    "case_id": case_code,
                    "verify_result": verify_result,
                }
            subject_masked = row["subject"] or ""
            body_masked = row["body_masked"] or ""

    record_pii_access(
        case_code,
        action="approve_unmask",
        actor_user_id=actor_user_id,
        role=actor_role,
        details={"draft_version_id": draft_version_id},
    )
    subject_unmasked = _clean_outbound_text(unmask_text(case_code, subject_masked or ""))
    body_unmasked = _clean_outbound_text(unmask_text(case_code, body_masked or ""))

    with sqlite3.connect(settings.sqlite_path) as conn:
        current_status = conn.execute("SELECT status FROM cases WHERE id = ?", (case_id,)).fetchone()[0]
        validate_transition(current_status, "lezarva")
        conn.execute(
            """
            INSERT INTO messages (case_id, direction, raw_text_masked, channel_payload)
            VALUES (?, 'outbound_mock', ?, ?)
            """,
            (
                case_id,
                body_masked or "",
                json.dumps(
                    {
                        "mock_sent": True,
                        "subject_masked_len": len(subject_masked or ""),
                        "body_masked_len": len(body_masked or ""),
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        conn.execute(
            "UPDATE cases SET status = 'lezarva', updated_at = ? WHERE id = ?",
            (_utc_now(), case_id),
        )
        conn.commit()

    record_audit_event(
        case_code,
        "draft_approved_mock_send",
        {
            "draft_version_id": draft_version_id,
            "subject_unmasked_len": len(subject_unmasked),
            "body_unmasked_len": len(body_unmasked),
            "mock_sent": True,
        },
        actor_user_id=actor_user_id,
    )

    return {
        "case_id": case_code,
        "status": "lezarva",
        "mock_sent": True,
        "subject_unmasked": subject_unmasked,
        "body_unmasked": body_unmasked,
    }
