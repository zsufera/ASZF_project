from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from config.settings import settings

USERS_PATH = Path("config/users.yaml")
POC_DEMO_PASSWORDS = {
    "ui_demo": "ui_demo",
    "supervisor_demo": "supervisor_demo",
}


def load_users_config() -> list[dict[str, Any]]:
    if not USERS_PATH.exists():
        return []
    payload = yaml.safe_load(USERS_PATH.read_text(encoding="utf-8")) or {}
    return list(payload.get("users", []))


def verify_login(username: str, password: str) -> dict[str, Any] | None:
    for user in load_users_config():
        if user.get("username") != username:
            continue
        expected = POC_DEMO_PASSWORDS.get(username, username)
        if password == expected:
            return {"username": username, "role": user.get("role", "ui")}
    return None


def ensure_users_in_db() -> None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        for user in load_users_config():
            username = user.get("username")
            if not username:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO users (username, password_hash, role, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (username, user.get("password_hash", ""), user.get("role", "ui")),
            )
        conn.commit()


def get_user_id(username: str) -> int | None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? AND is_active = 1 LIMIT 1",
            (username,),
        ).fetchone()
    return int(row[0]) if row else None


def get_user_role(username: str) -> str | None:
    with sqlite3.connect(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username = ? AND is_active = 1 LIMIT 1",
            (username,),
        ).fetchone()
    return str(row[0]) if row else None
