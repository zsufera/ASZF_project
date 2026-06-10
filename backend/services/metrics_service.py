"""Operational KPI aggregation from existing audit and case data.

All metrics are calculated from already recorded SQLite tables. The output is
aggregate-only and does not include PII.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from statistics import median
from typing import Any

from config.settings import settings

UNCHANGED_THRESHOLD = 0.05
REWRITE_THRESHOLD = 0.30


def _parse_ts(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _handling_time(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT MIN(CASE WHEN event_type = 'case_iteration' THEN created_at END) AS started,
               MAX(CASE WHEN event_type = 'draft_approved_mock_send' THEN created_at END) AS approved
        FROM audit_events
        GROUP BY case_id
        """
    ).fetchall()
    durations: list[float] = []
    for started, approved in rows:
        t0, t1 = _parse_ts(started), _parse_ts(approved)
        if t0 and t1 and t1 >= t0:
            durations.append((t1 - t0).total_seconds())
    if not durations:
        return {"avg_seconds": None, "median_seconds": None, "sample_size": 0}
    return {
        "avg_seconds": round(sum(durations) / len(durations), 1),
        "median_seconds": round(median(durations), 1),
        "sample_size": len(durations),
    }


def _draft_acceptance(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT (SELECT body_masked FROM draft_versions v
                WHERE v.case_id = c.id ORDER BY version_no ASC LIMIT 1),
               (SELECT body_masked FROM draft_versions v
                WHERE v.case_id = c.id ORDER BY version_no DESC LIMIT 1)
        FROM cases c
        WHERE c.status = 'lezarva'
        """
    ).fetchall()
    bands = {"unchanged": 0, "light_edit": 0, "rewrite": 0}
    ratios: list[float] = []
    for first_body, final_body in rows:
        if not first_body or final_body is None:
            continue
        edit_ratio = 1.0 - SequenceMatcher(None, first_body, final_body).ratio()
        ratios.append(edit_ratio)
        if edit_ratio < UNCHANGED_THRESHOLD:
            bands["unchanged"] += 1
        elif edit_ratio < REWRITE_THRESHOLD:
            bands["light_edit"] += 1
        else:
            bands["rewrite"] += 1
    return {
        **bands,
        "avg_edit_ratio": round(sum(ratios) / len(ratios), 3) if ratios else None,
        "sample_size": len(ratios),
    }


def _latest_category(conn: sqlite3.Connection, case_id: int) -> str:
    row = conn.execute(
        """
        SELECT payload FROM audit_events
        WHERE case_id = ? AND event_type = 'case_iteration'
        ORDER BY created_at DESC LIMIT 1
        """,
        (case_id,),
    ).fetchone()
    if not row or not row[0]:
        return "ismeretlen"
    try:
        return json.loads(row[0]).get("category") or "ismeretlen"
    except json.JSONDecodeError:
        return "ismeretlen"


def _feedback(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT case_id, payload FROM audit_events WHERE event_type = 'ui_feedback'"
    ).fetchall()
    good = bad = wrong_source = 0
    by_reason: dict[str, int] = {}
    by_category: dict[str, dict[str, int]] = {}
    for case_id, raw in rows:
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        rating = payload.get("rating")
        if rating == "jo":
            good += 1
        elif rating == "rossz":
            bad += 1
        if payload.get("wrong_source"):
            wrong_source += 1
        reason = payload.get("reason")
        if reason:
            by_reason[reason] = by_reason.get(reason, 0) + 1
        category = _latest_category(conn, case_id)
        entry = by_category.setdefault(category, {"good": 0, "bad": 0})
        if rating == "jo":
            entry["good"] += 1
        elif rating == "rossz":
            entry["bad"] += 1
    total = good + bad
    return {
        "good": good,
        "bad": bad,
        "wrong_source": wrong_source,
        "positive_rate": round(good / total, 3) if total else None,
        "by_reason": by_reason,
        "by_category": [
            {"category": category, **counts} for category, counts in sorted(by_category.items())
        ],
    }


def get_operational_metrics() -> dict[str, Any]:
    """Return live operational feedback KPIs as one aggregate object."""
    with sqlite3.connect(settings.sqlite_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        processed = conn.execute("SELECT COUNT(DISTINCT case_id) FROM draft_versions").fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM cases WHERE status = 'lezarva'").fetchone()[0]
        escalated = conn.execute("SELECT COUNT(*) FROM cases WHERE escalated = 1").fetchone()[0]
        handling = _handling_time(conn)
        acceptance = _draft_acceptance(conn)
        feedback = _feedback(conn)
    return {
        "case_funnel": {
            "total_cases": total,
            "processed_cases": processed,
            "closed_cases": closed,
            "adoption_rate": round(processed / total, 3) if total else 0.0,
        },
        "handling_time": handling,
        "draft_acceptance": acceptance,
        "feedback": feedback,
        "escalation": {
            "escalated_cases": escalated,
            "escalation_rate": round(escalated / total, 3) if total else 0.0,
        },
    }
