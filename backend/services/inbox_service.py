"""Inbox seeding and supervisor functions extracted from case_service.

Contains: seed_inbox_from_samples, get_supervisor_queue, get_supervisor_stats.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.case_service import SAMPLE_EMAIL_DIR, _utc_now, list_inbox
from backend.masking import mask_text, sender_email_key
from backend.metadata import load_manifest_summary
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory


def _sync_mock_customer_candidates_for_existing_samples() -> int:
    customer_directory = MockCustomerDirectory()
    synced = 0
    with sqlite3.connect(settings.sqlite_path) as conn:
        for path in sorted(SAMPLE_EMAIL_DIR.glob("email-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            candidates = customer_directory.lookup_by_email(payload.get("felado_email", ""))
            if not candidates:
                continue
            case_code = f"CASE-{payload['email_id']}"
            row = conn.execute(
                "SELECT id, selected_customer_id FROM cases WHERE case_code = ?",
                (case_code,),
            ).fetchone()
            if not row:
                continue
            case_id, selected_customer_id = row
            selected_row = conn.execute(
                """
                SELECT customer_id
                FROM customer_candidates
                WHERE case_id = ? AND selected = 1
                LIMIT 1
                """,
                (case_id,),
            ).fetchone()
            selected_id = selected_customer_id or (selected_row[0] if selected_row else None)
            conn.execute("DELETE FROM customer_candidates WHERE case_id = ? AND source = 'mock'", (case_id,))
            for candidate in candidates:
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
                        1 if candidate["customer_id"] == selected_id else 0,
                    ),
                )
            synced += 1
        conn.commit()
    return synced


def seed_inbox_from_samples(force: bool = False) -> dict[str, Any]:
    customer_directory = MockCustomerDirectory()
    with sqlite3.connect(settings.sqlite_path) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        if existing and not force:
            synced = _sync_mock_customer_candidates_for_existing_samples()
            return {"seeded": 0, "skipped": True, "existing": existing, "mock_customers_synced": synced}
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
                "customer_candidates": customer_directory.lookup_by_email(sender),
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
            for candidate in item["customer_candidates"]:
                conn.execute(
                    """
                    INSERT INTO customer_candidates
                    (case_id, source, customer_id, customer_name, link_url, selected)
                    VALUES (?, ?, ?, ?, ?, 0)
                    """,
                    (
                        case_id,
                        candidate.get("source", "mock"),
                        candidate["customer_id"],
                        candidate["customer_name"],
                        candidate.get("link_url"),
                    ),
                )
            seeded += 1
        conn.commit()
    return {"seeded": seeded, "skipped": False}


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
