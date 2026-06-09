from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agent.runner import run_agent
from backend.audit_service import record_audit_event, record_iteration_audit, record_pii_access
from backend.draft import ensure_disclaimer, strip_source_markers
from backend.history import get_history
from backend.masking import mask_text, sender_email_key, unmask_text
from backend.metadata import load_manifest_summary
from backend.workflow import validate_transition
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory
from security.rbac import require_permission


SAMPLE_EMAIL_DIR = Path("data/sample_emails")
CATEGORY_LABELS = {
    "szamlazas": "Számlázás",
    "dijemeles": "Díjemelés",
    "hibabejelentes_szolgaltataskieses": "Hibabejelentés",
    "szerzodesfelmondas_modositas": "Szerződés",
    "lefedettseg": "Lefedettség",
    "eszkoz_keszulek": "Eszköz",
    "adatvedelem": "Adatvédelem",
    "egyeb": "Egyéb",
}
STATUS_LABELS = {
    "uj": "Új",
    "folyamatban": "Folyamatban",
    "eszkalalva": "Eszkalálva",
    "jovahagyasra_var": "Jóváhagyásra vár",
    "lezarva": "Lezárva",
}
CHANNEL_LABELS = {
    "email": "Email",
    "chat": "Chat",
    "phone": "Telefon",
    "postal": "Postai",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sla_days_remaining(created_at: str, fallback_days: int | None = None) -> int:
    days = fallback_days or settings.sla_fallback_days
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return days
    elapsed = (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).days
    return max(0, days - elapsed)


def _load_policies() -> dict[str, Any]:
    path = Path("config/policies.yaml")
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _case_row_to_inbox_item(row: sqlite3.Row, payload: dict[str, Any]) -> dict[str, Any]:
    category = payload.get("category") or payload.get("expected_category")
    return {
        "case_id": row["case_code"],
        "channel": row["channel"],
        "channel_label": CHANNEL_LABELS.get(row["channel"], row["channel"]),
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"]),
        "priority": row["priority"] or "normal",
        "confidence": row["confidence"],
        "escalated": bool(row["escalated"]),
        "escalation_reasons": json.loads(row["escalation_reasons"]) if row["escalation_reasons"] else [],
        "sender_email_masked": row["sender_email_masked"],
        "sender_email_key": row["sender_email_key"],
        "service_provider": row["service_provider"],
        "subject": payload.get("subject") or "",
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category or "—"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "sla_days_remaining": _sla_days_remaining(row["created_at"]),
    }


def seed_inbox_from_samples(force: bool = False) -> dict[str, Any]:
    with sqlite3.connect(settings.sqlite_path) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        if existing and not force:
            return {"seeded": 0, "skipped": True, "existing": existing}
        existing_codes = {
            row[0]
            for row in conn.execute("SELECT case_code FROM cases").fetchall()
        }

    prepared: list[dict[str, Any]] = []
    for path in sorted(SAMPLE_EMAIL_DIR.glob("email-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        case_code = f"CASE-{payload['email_id']}"
        if case_code in existing_codes and not force:
            continue
        sender = payload.get("felado_email", "")
        masked_sender = mask_text(case_code, sender)["masked_text"] if sender else None
        sender_key = sender_email_key(sender)
        masked_body = mask_text(case_code, payload.get("torzs", ""))["masked_text"]
        prepared.append(
            {
                "case_code": case_code,
                "exists": case_code in existing_codes,
                "masked_sender": masked_sender,
                "sender_key": sender_key,
                "masked_body": masked_body,
                "channel_payload": json.dumps(
                    {
                        "subject": payload.get("targy"),
                        "expected_category": payload.get("varht_kategoria"),
                        "email_id": payload.get("email_id"),
                        "edge_case": payload.get("edge_case"),
                    },
                    ensure_ascii=False,
                ),
                "priority": "surgos" if payload.get("varhato_eszkalacio") else "normal",
                "status": "eszkalalva" if payload.get("varhato_eszkalacio") else "uj",
                "service_provider": payload.get("szolgaltato"),
            }
        )

    with sqlite3.connect(settings.sqlite_path) as conn:
        if force:
            conn.execute("DELETE FROM customer_candidates")
            conn.execute("DELETE FROM draft_versions")
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM agent_runs")
            conn.execute("DELETE FROM audit_events")
            conn.execute("DELETE FROM history_links")
            conn.execute("DELETE FROM cases")

        seeded = 0
        for item in prepared:
            conn.execute(
                """
                INSERT INTO cases (
                    case_code, channel, status, priority, sender_email_masked,
                    sender_email_key, service_provider, created_at, updated_at
                ) VALUES (?, 'email', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["case_code"],
                    item["status"],
                    item["priority"],
                    item["masked_sender"],
                    item["sender_key"],
                    item["service_provider"],
                    _utc_now(),
                    _utc_now(),
                ),
            )
            case_id = conn.execute(
                "SELECT id FROM cases WHERE case_code = ?",
                (item["case_code"],),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO messages (case_id, direction, raw_text_masked, channel_payload, message_type)
                VALUES (?, 'inbound', ?, ?, 'panasz')
                """,
                (case_id, item["masked_body"], item["channel_payload"]),
            )
            seeded += 1
        conn.commit()
    return {"seeded": seeded, "skipped": False}


def list_inbox(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    search: str | None = None,
    sort_by: str = "priority",
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if priority:
        clauses.append("c.priority = ?")
        params.append(priority)
    if status:
        clauses.append("c.status = ?")
        params.append(status)
    if channel:
        clauses.append("c.channel = ?")
        params.append(channel)
    if search:
        clauses.append("(c.case_code LIKE ? OR c.sender_email_masked LIKE ? OR m.channel_payload LIKE ?)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern])

    order = {
        "priority": "CASE c.priority WHEN 'surgos' THEN 0 ELSE 1 END, c.updated_at DESC",
        "sla": "c.created_at ASC",
        "created_at": "c.created_at DESC",
    }.get(sort_by, "c.updated_at DESC")

    query = f"""
        SELECT c.*, m.channel_payload, m.raw_text_masked
        FROM cases c
        LEFT JOIN messages m ON m.case_id = c.id AND m.direction = 'inbound'
        WHERE {' AND '.join(clauses)}
        ORDER BY {order}
    """
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        payload = {}
        if row["channel_payload"]:
            try:
                payload = json.loads(row["channel_payload"])
            except json.JSONDecodeError:
                payload = {}
        item = _case_row_to_inbox_item(row, payload)
        if category and item.get("category") != category:
            continue
        items.append(item)
    return items


def get_case_detail(case_code: str) -> dict[str, Any] | None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT c.*, m.raw_text_masked, m.channel_payload
            FROM cases c
            LEFT JOIN messages m ON m.case_id = c.id AND m.direction = 'inbound'
            WHERE c.case_code = ?
            ORDER BY m.created_at DESC
            LIMIT 1
            """,
            (case_code,),
        ).fetchone()
        if not row:
            return None

        payload = json.loads(row["channel_payload"]) if row["channel_payload"] else {}
        drafts = conn.execute(
            """
            SELECT id, version_no, subject, body_masked, output_mode, disclaimer_applied,
                   citations, verify_result, created_at
            FROM draft_versions
            WHERE case_id = ?
            ORDER BY version_no DESC
            """,
            (row["id"],),
        ).fetchall()
        candidates = conn.execute(
            """
            SELECT customer_id, customer_name, link_url, source, selected
            FROM customer_candidates
            WHERE case_id = ?
            ORDER BY selected DESC, id ASC
            """,
            (row["id"],),
        ).fetchall()
        latest_run = conn.execute(
            """
            SELECT state_snapshot, started_at, ended_at
            FROM agent_runs
            WHERE case_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (row["id"],),
        ).fetchone()

    agent_state = {}
    if latest_run and latest_run["state_snapshot"]:
        try:
            agent_state = json.loads(latest_run["state_snapshot"])
        except json.JSONDecodeError:
            agent_state = {}

    draft_versions = [
        {
            "id": draft["id"],
            "version_no": draft["version_no"],
            "subject": draft["subject"],
            "body_masked": draft["body_masked"],
            "output_mode": draft["output_mode"],
            "disclaimer_applied": bool(draft["disclaimer_applied"]),
            "citations": json.loads(draft["citations"]) if draft["citations"] else [],
            "verify_result": json.loads(draft["verify_result"]) if draft["verify_result"] else {},
            "created_at": draft["created_at"],
        }
        for draft in drafts
    ]

    return {
        **_case_row_to_inbox_item(row, payload),
        "inbound_text_masked": row["raw_text_masked"] or "",
        "subject": payload.get("subject") or "",
        "draft_versions": draft_versions,
        "customer_candidates": [
            {
                "customer_id": candidate["customer_id"],
                "customer_name": candidate["customer_name"],
                "link_url": candidate["link_url"],
                "source": candidate["source"],
                "selected": bool(candidate["selected"]),
            }
            for candidate in candidates
        ],
        "agent_state": agent_state,
        "agent_run_at": latest_run["ended_at"] if latest_run else None,
    }


def _get_case_db_id(case_code: str) -> int | None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        row = conn.execute("SELECT id FROM cases WHERE case_code = ?", (case_code,)).fetchone()
    return int(row[0]) if row else None


def _clean_outbound_text(text: str) -> str:
    """Az ügyfélhez kimenő szövegből eltávolítja a belső [Sn] forrás-jelölőket."""
    return strip_source_markers(text)


def create_ad_hoc_case(
    channel: str,
    input_text: str,
    sender_email: str | None = None,
    service_provider: str | None = None,
) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    case_code = f"CASE-ADHOC-{stamp}-{uuid.uuid4().hex[:8]}"
    masked_body = mask_text(case_code, input_text)["masked_text"]
    masked_sender = mask_text(case_code, sender_email)["masked_text"] if sender_email else None
    sender_key = sender_email_key(sender_email)
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO cases (case_code, channel, status, priority, sender_email_masked, sender_email_key, service_provider)
            VALUES (?, ?, 'uj', 'normal', ?, ?, ?)
            """,
            (case_code, channel, masked_sender, sender_key, service_provider),
        )
        case_id = conn.execute("SELECT id FROM cases WHERE case_code = ?", (case_code,)).fetchone()[0]
        conn.execute(
            """
            INSERT INTO messages (case_id, direction, raw_text_masked, channel_payload)
            VALUES (?, 'inbound', ?, ?)
            """,
            (
                case_id,
                masked_body,
                json.dumps({"subject": input_text.splitlines()[0][:120]}, ensure_ascii=False),
            ),
        )
        conn.commit()
    return case_code


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
                return {"error": "Draft verziĂł nem talĂˇlhatĂł", "case_id": case_code}
            verify_result = json.loads(row["verify_result"]) if row["verify_result"] else {}
            if (
                verify_result.get("warning")
                or verify_result.get("ungrounded_count", 0)
                or verify_result.get("missing_mandatory")
            ):
                return {
                    "error": "A draft nem hagyhatĂł jĂłvĂˇ, mert a forrĂˇsoltsĂˇgi ellenĹ‘rzĂ©s hibĂˇt jelzett.",
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


def transition_case_status(
    case_code: str,
    target_status: str,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    require_permission(actor_role, "change_status")
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ügy nem található"}
    with sqlite3.connect(settings.sqlite_path) as conn:
        current = conn.execute("SELECT status FROM cases WHERE id = ?", (case_id,)).fetchone()[0]
        validate_transition(current, target_status)
        conn.execute(
            "UPDATE cases SET status = ?, updated_at = ? WHERE id = ?",
            (target_status, _utc_now(), case_id),
        )
        conn.commit()
    record_audit_event(
        case_code,
        "status_transition",
        {"from": current, "to": target_status},
        actor_user_id=actor_user_id,
    )
    return {"case_id": case_code, "status": target_status, "previous_status": current}


def submit_feedback(
    case_code: str,
    rating: str,
    wrong_source: bool = False,
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ügy nem található"}
    record_audit_event(
        case_code,
        "ui_feedback",
        {"rating": rating, "wrong_source": wrong_source},
        actor_user_id=actor_user_id,
    )
    return {"case_id": case_code, "rating": rating, "wrong_source": wrong_source}


def get_supervisor_queue() -> list[dict[str, Any]]:
    return list_inbox(status="eszkalalva", sort_by="priority")


def get_supervisor_stats() -> dict[str, Any]:
    with sqlite3.connect(settings.sqlite_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        escalated = conn.execute("SELECT COUNT(*) FROM cases WHERE escalated = 1").fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM cases WHERE status = 'lezarva'").fetchone()[0]
        feedback_good = conn.execute(
            """
            SELECT COUNT(*) FROM audit_events
            WHERE event_type = 'ui_feedback' AND payload LIKE '%"rating": "jo"%'
            """
        ).fetchone()[0]
        feedback_bad = conn.execute(
            """
            SELECT COUNT(*) FROM audit_events
            WHERE event_type = 'ui_feedback' AND payload LIKE '%"rating": "rossz"%'
            """
        ).fetchone()[0]
        by_operator = conn.execute(
            """
            SELECT u.username, COUNT(a.id) as processed
            FROM audit_events a
            JOIN users u ON u.id = a.actor_user_id
            WHERE a.event_type = 'agent_processed'
            GROUP BY u.username
            """
        ).fetchall()
    manifest = load_manifest_summary()
    return {
        "total_cases": total,
        "escalated_cases": escalated,
        "closed_cases": closed,
        "escalation_rate": round(escalated / total, 3) if total else 0.0,
        "feedback_good": feedback_good,
        "feedback_bad": feedback_bad,
        "by_operator": [{"username": row[0], "processed": row[1]} for row in by_operator],
        "aszf_version": manifest.get("aszf_version"),
    }
