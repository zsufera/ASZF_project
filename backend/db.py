import os
import sqlite3
from pathlib import Path

from config.settings import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ui', 'supervisor')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_code TEXT NOT NULL UNIQUE,
    channel TEXT NOT NULL CHECK(channel IN ('email', 'chat', 'phone', 'postal')),
    status TEXT NOT NULL CHECK(status IN ('uj', 'folyamatban', 'eszkalalva', 'jovahagyasra_var', 'lezarva')),
    priority TEXT CHECK(priority IN ('surgos', 'normal')),
    confidence REAL,
    escalated INTEGER NOT NULL DEFAULT 0,
    escalation_reasons TEXT,
    sender_email_masked TEXT,
    service_provider TEXT,
    selected_customer_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('inbound', 'draft', 'outbound_mock')),
    raw_text_masked TEXT,
    channel_payload TEXT,
    language TEXT,
    message_type TEXT CHECK(message_type IN ('panasz', 'nem_panasz')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS draft_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    subject TEXT,
    body_masked TEXT,
    output_mode TEXT CHECK(output_mode IN ('automata', 'hitl')),
    disclaimer_applied INTEGER NOT NULL DEFAULT 0,
    citations TEXT,
    verify_result TEXT,
    created_by_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(created_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS history_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    related_case_id INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT 'same_sender_email',
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(related_case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS customer_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('mock', 'integration')),
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    link_url TEXT,
    selected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    prompt_version_bundle TEXT,
    model_profile TEXT,
    state_snapshot TEXT,
    started_at TEXT,
    ended_at TEXT,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS pii_token_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    token TEXT NOT NULL,
    original_value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_user_id INTEGER,
    payload TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_cases_status_priority_updated_at
ON cases(status, priority, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cases_channel_created_at
ON cases(channel, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_case_created_at
ON messages(case_id, created_at);

CREATE INDEX IF NOT EXISTS idx_customer_candidates_case_selected
ON customer_candidates(case_id, selected);

CREATE INDEX IF NOT EXISTS idx_audit_events_case_created_at
ON audit_events(case_id, created_at);
"""


def init_db(db_path: str | None = None) -> None:
    target = db_path or settings.sqlite_path
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"SQLite schema initialized at: {os.path.abspath(settings.sqlite_path)}")
