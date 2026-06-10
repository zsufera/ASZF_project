from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.audit_service import record_audit_event
from backend.draft import strip_source_markers
from backend.masking import mask_text, sender_email_key
from backend.workflow import validate_transition
from config.settings import settings
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


def _sla_due_at(created_at: str, fallback_days: int | None = None) -> str | None:
    days = fallback_days or settings.sla_fallback_days
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (created.astimezone(timezone.utc) + timedelta(days=days)).isoformat()


def _row_value(row: sqlite3.Row, key: str) -> Any:
    return row[key] if key in row.keys() else None


def _username_for_id(user_id: int | None) -> str | None:
    if not user_id:
        return None
    with sqlite3.connect(settings.sqlite_path) as conn:
        user = conn.execute(
            "SELECT username FROM users WHERE id = ? AND is_active = 1 LIMIT 1",
            (user_id,),
        ).fetchone()
    return str(user[0]) if user else None


def _user_id_for_username(username: str) -> int | None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ? AND is_active = 1 LIMIT 1",
            (username,),
        ).fetchone()
    return int(user[0]) if user else None


def _sender_email_display(masked_sender: str | None, stable_key: str | None) -> str:
    if stable_key:
        digest = stable_key.split(":", 1)[-1]
        return f"Email #{digest[:8]}"
    return "Maszkolt email" if masked_sender else ""


def _load_policies() -> dict[str, Any]:
    path = Path("config/policies.yaml")
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _case_row_to_inbox_item(row: sqlite3.Row, payload: dict[str, Any]) -> dict[str, Any]:
    category = payload.get("category") or payload.get("expected_category")
    assignee_user_id = _row_value(row, "assignee_user_id")
    claimed_by_user_id = _row_value(row, "claimed_by_user_id")
    sla_due_at = _row_value(row, "sla_due_at") or _sla_due_at(row["created_at"])
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
        "sender_email_display": _sender_email_display(row["sender_email_masked"], row["sender_email_key"]),
        "service_provider": row["service_provider"],
        "subject": payload.get("subject") or "",
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category or "—"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "assignee_user_id": assignee_user_id,
        "assignee_username": _username_for_id(assignee_user_id),
        "claimed_by_user_id": claimed_by_user_id,
        "claimed_by_username": _username_for_id(claimed_by_user_id),
        "claimed_at": _row_value(row, "claimed_at"),
        "sla_due_at": sla_due_at,
        "sla_breached_at": _row_value(row, "sla_breached_at"),
        "sla_days_remaining": _sla_days_remaining(row["created_at"]),
    }


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


def claim_case(
    case_code: str,
    username: str,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    require_permission(actor_role, "change_status")
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ăśgy nem talĂˇlhatĂł"}
    claimed_by_user_id = _user_id_for_username(username)
    if not claimed_by_user_id:
        return {"error": "felhasznĂˇlĂł nem talĂˇlhatĂł"}
    claimed_at = _utc_now()
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            UPDATE cases
            SET claimed_by_user_id = ?, claimed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (claimed_by_user_id, claimed_at, claimed_at, case_id),
        )
        conn.commit()
    record_audit_event(
        case_code,
        "case_claimed",
        {"claimed_by_username": username, "claimed_at": claimed_at},
        actor_user_id=actor_user_id,
    )
    return {
        "case_id": case_code,
        "claimed_by_user_id": claimed_by_user_id,
        "claimed_by_username": username,
        "claimed_at": claimed_at,
    }


def assign_case(
    case_code: str,
    assignee_username: str,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    require_permission(actor_role, "change_status")
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ăśgy nem talĂˇlhatĂł"}
    assignee_user_id = _user_id_for_username(assignee_username)
    if not assignee_user_id:
        return {"error": "felhasznĂˇlĂł nem talĂˇlhatĂł"}
    now = _utc_now()
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE cases SET assignee_user_id = ?, updated_at = ? WHERE id = ?",
            (assignee_user_id, now, case_id),
        )
        conn.commit()
    record_audit_event(
        case_code,
        "case_assigned",
        {"assignee_username": assignee_username},
        actor_user_id=actor_user_id,
    )
    return {
        "case_id": case_code,
        "assignee_user_id": assignee_user_id,
        "assignee_username": assignee_username,
    }


def release_case(
    case_code: str,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    require_permission(actor_role, "change_status")
    case_id = _get_case_db_id(case_code)
    if not case_id:
        return {"error": "Ăśgy nem talĂˇlhatĂł"}
    now = _utc_now()
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE cases SET claimed_by_user_id = NULL, claimed_at = NULL, updated_at = ? WHERE id = ?",
            (now, case_id),
        )
        conn.commit()
    record_audit_event(
        case_code,
        "case_released",
        {},
        actor_user_id=actor_user_id,
    )
    return {"case_id": case_code, "claimed_by_user_id": None, "claimed_by_username": None, "claimed_at": None}


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



# ── Re-exports for backward compatibility ──────────────────────────────
# These functions have been moved to dedicated modules but are re-exported
# here so that existing imports (tests, integrations) keep working.
from backend.services.case_processing import approve_draft, process_case, save_draft_version  # noqa: E402,F401
from backend.services.inbox_service import (  # noqa: E402,F401
    get_supervisor_queue,
    get_supervisor_stats,
    seed_inbox_from_samples,
)
