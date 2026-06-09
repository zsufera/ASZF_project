from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from backend.masking import sender_email_key as build_sender_email_key
from config.settings import settings


MASKED_EMAIL_TOKEN_RE = re.compile(r"^\[MASK_EMAIL_\d+\]$")


def _empty_history(address: str) -> dict[str, Any]:
    return {
        "items": [],
        "summary_masked": "0 korabbi uzenet",
        "is_repeated": False,
        "address": address,
    }


def get_history(address: str, limit: int = 20, sender_email_key: str | None = None) -> dict[str, Any]:
    if not sender_email_key and "@" in (address or ""):
        sender_email_key = build_sender_email_key(address)
    if not sender_email_key and MASKED_EMAIL_TOKEN_RE.fullmatch(address or ""):
        return _empty_history(address)
    lookup_column = "c.sender_email_key" if sender_email_key else "c.sender_email_masked"
    lookup_value = sender_email_key or address
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT
                c.case_code,
                c.status,
                c.created_at,
                m.raw_text_masked,
                m.message_type,
                m.channel_payload
            FROM cases c
            LEFT JOIN messages m ON m.case_id = c.id AND m.direction = 'inbound'
            WHERE {lookup_column} = ?
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (lookup_value, limit),
        ).fetchall()

    items: list[dict[str, Any]] = []
    categories: list[str] = []
    for row in rows:
        payload = {}
        if row["channel_payload"]:
            try:
                payload = json.loads(row["channel_payload"])
            except json.JSONDecodeError:
                payload = {}
        category = payload.get("category")
        if category:
            categories.append(category)
        subject = payload.get("subject") or (row["raw_text_masked"] or "").splitlines()[0][:120]
        items.append(
            {
                "case_id": row["case_code"],
                "date": row["created_at"],
                "subject": subject,
                "category": category,
                "status": row["status"],
                "message_type": row["message_type"],
            }
        )

    repeated_categories = {category for category in categories if categories.count(category) > 1}
    summary_parts = [f"{len(items)} korabbi uzenet"]
    if repeated_categories:
        summary_parts.append(f"ismetlodo kategoriak: {', '.join(sorted(repeated_categories))}")
    return {
        "items": items,
        "summary_masked": "; ".join(summary_parts),
        "is_repeated": bool(repeated_categories),
        "address": address,
    }
