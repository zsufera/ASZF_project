from __future__ import annotations

import hashlib
import re
import sqlite3
from typing import Any

from config.settings import settings


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+36|06)?[\s-]?(?:1|20|30|31|50|70)[\s-]?\d{3}[\s-]?\d{3,4}\b")
CUSTOMER_ID_PATTERN = re.compile(
    r"\b(?:ügyfél(?:azonosító|szám)|ugyfel(?:azonosito|szam)|ügyfélszám|ugyfelszam)\s*[:#]?\s*([A-Za-z0-9-]+)\b",
    re.I,
)
SIM_PATTERN = re.compile(r"\b36\d{9}\b")

PII_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pii_token_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    token TEXT NOT NULL,
    original_value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(PII_TABLE_SQL)


def _next_token(label: str, counters: dict[str, int]) -> str:
    counters[label] = counters.get(label, 0) + 1
    return f"[MASK_{label.upper()}_{counters[label]}]"


def sender_email_key(address: str | None) -> str | None:
    """Stable non-PII lookup key for same-sender history.

    Mask tokens are intentionally case-local and reusable, so they cannot
    identify a sender across cases.
    """
    normalized = (address or "").strip().lower()
    if not normalized:
        return None
    return "email:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _store_token(case_id: str, token: str, original: str) -> None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO pii_token_map (case_id, token, original_value) VALUES (?, ?, ?)",
            (case_id, token, original),
        )
        conn.commit()


def _replace_pattern(
    text: str,
    pattern: re.Pattern[str],
    label: str,
    case_id: str,
    counters: dict[str, int],
    group: int = 0,
) -> str:
    result = text
    for match in reversed(list(pattern.finditer(text))):
        value = match.group(group)
        token = _next_token(label, counters)
        _store_token(case_id, token, value)
        result = result[: match.start(group)] + token + result[match.end(group) :]
    return result


def mask_text(case_id: str, text: str) -> dict[str, Any]:
    counters: dict[str, int] = {}
    masked = _replace_pattern(text, EMAIL_PATTERN, "email", case_id, counters)
    masked = _replace_pattern(masked, PHONE_PATTERN, "phone", case_id, counters)
    masked = _replace_pattern(masked, CUSTOMER_ID_PATTERN, "customer_id", case_id, counters, group=1)
    masked = _replace_pattern(masked, SIM_PATTERN, "sim", case_id, counters)
    return {
        "masked_text": masked,
        "token_count": sum(counters.values()),
        "token_types": counters,
    }


def unmask_text(case_id: str, text: str) -> str:
    with sqlite3.connect(settings.sqlite_path) as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT token, original_value
            FROM pii_token_map
            WHERE case_id = ?
            ORDER BY id DESC
            """,
            (case_id,),
        ).fetchall()
    unmasked = text
    for token, original in rows:
        unmasked = unmasked.replace(token, original)
    return unmasked
