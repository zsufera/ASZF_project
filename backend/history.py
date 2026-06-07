from __future__ import annotations

import json
import sqlite3
from typing import Any

from config.settings import settings


def get_history(address: str, limit: int = 20) -> dict[str, Any]:
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                c.case_code,
                c.status,
                c.created_at,
                m.raw_text_masked,
                m.message_type,
                m.channel_payload
            FROM cases c
            LEFT JOIN messages m ON m.case_id = c.id AND m.direction = 'inbound'
            WHERE c.sender_email_masked = ?
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (address, limit),
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
