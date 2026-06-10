from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from backend.audit_service import record_audit_event
from backend.case_service import create_ad_hoc_case
from backend.masking import mask_text
from config.settings import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_session(conn: sqlite3.Connection, session_id: str, username: str | None = None) -> None:
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO copilot_sessions (session_id, username, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            username = COALESCE(excluded.username, copilot_sessions.username),
            updated_at = excluded.updated_at
        """,
        (session_id, username, now, now),
    )


def record_copilot_turn(
    session_id: str,
    role: str,
    content: str,
    username: str | None = None,
    sources: list[dict[str, Any]] | None = None,
    timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if role not in {"user", "assistant", "system"}:
        return {"error": "ervenytelen copilot szerep"}
    masked = mask_text(session_id, content)["masked_text"]
    with sqlite3.connect(settings.sqlite_path) as conn:
        _ensure_session(conn, session_id, username)
        cursor = conn.execute(
            """
            INSERT INTO copilot_turns (session_id, role, content_masked, sources, timeline, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                masked,
                json.dumps(sources or [], ensure_ascii=False),
                json.dumps(timeline or [], ensure_ascii=False),
                _utc_now(),
            ),
        )
        conn.commit()
        turn_id = int(cursor.lastrowid)
    return {"session_id": session_id, "turn_id": turn_id, "role": role}


def list_copilot_sessions(username: str | None = None) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if username:
        clauses.append("(s.username = ? OR s.username IS NULL)")
        params.append(username)
    query = f"""
        SELECT s.session_id, s.username, s.case_code, s.created_at, s.updated_at,
               COUNT(t.id) AS turn_count,
               MAX(t.content_masked) AS last_content_masked
        FROM copilot_sessions s
        LEFT JOIN copilot_turns t ON t.session_id = s.session_id
        WHERE {' AND '.join(clauses)}
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT 50
    """
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "session_id": row["session_id"],
            "username": row["username"],
            "case_id": row["case_code"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "turn_count": row["turn_count"],
            "last_content_masked": row["last_content_masked"] or "",
        }
        for row in rows
    ]


def handoff_copilot_session(
    session_id: str,
    username: str | None = None,
    selected_turn_ids: list[int] | None = None,
) -> dict[str, Any]:
    params: list[Any] = [session_id]
    id_filter = ""
    if selected_turn_ids:
        placeholders = ",".join("?" for _ in selected_turn_ids)
        id_filter = f"AND id IN ({placeholders})"
        params.extend(selected_turn_ids)

    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        turns = conn.execute(
            f"""
            SELECT id, role, content_masked, created_at
            FROM copilot_turns
            WHERE session_id = ? {id_filter}
            ORDER BY created_at ASC, id ASC
            """,
            params,
        ).fetchall()

    if not turns:
        return {"error": "nincs atadhato copilot turn"}

    full_text = "\n".join(f"{turn['role']}: {turn['content_masked']}" for turn in turns)
    case_code = create_ad_hoc_case(channel="chat", input_text=full_text)
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE copilot_sessions SET case_code = ?, updated_at = ? WHERE session_id = ?",
            (case_code, _utc_now(), session_id),
        )
        conn.commit()
    record_audit_event(
        case_code,
        "copilot_handoff",
        {
            "session_id": session_id,
            "username": username,
            "turn_ids": [turn["id"] for turn in turns],
        },
    )
    return {"session_id": session_id, "case_id": case_code, "turn_count": len(turns)}
