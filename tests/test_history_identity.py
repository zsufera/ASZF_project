import json
import sqlite3

from backend.db import init_db
from backend.history import get_history
from backend.masking import mask_text, sender_email_key


def _insert_case(db_path, case_code: str, masked_sender: str, stable_key: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cases (
                case_code, channel, status, priority, sender_email_masked,
                sender_email_key, service_provider
            )
            VALUES (?, 'email', 'uj', 'normal', ?, ?, 'ONE')
            """,
            (case_code, masked_sender, stable_key),
        )
        case_id = conn.execute("SELECT id FROM cases WHERE case_code = ?", (case_code,)).fetchone()[0]
        conn.execute(
            """
            INSERT INTO messages (case_id, direction, raw_text_masked, channel_payload, message_type)
            VALUES (?, 'inbound', ?, ?, 'panasz')
            """,
            (
                case_id,
                "Szamlazasi kifogas",
                json.dumps({"subject": case_code, "category": "szamlazas"}),
            ),
        )
        conn.commit()


def test_history_uses_stable_sender_key_not_reusable_mask_token(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.history.settings.sqlite_path", str(db_path))
    init_db()

    alice_masked = mask_text("CASE-ALICE", "alice@example.invalid")["masked_text"]
    bob_masked = mask_text("CASE-BOB", "bob@example.invalid")["masked_text"]
    assert alice_masked == bob_masked == "[MASK_EMAIL_1]"

    _insert_case(db_path, "CASE-ALICE", alice_masked, sender_email_key("alice@example.invalid"))
    _insert_case(db_path, "CASE-BOB", bob_masked, sender_email_key("bob@example.invalid"))

    history = get_history(alice_masked, sender_email_key=sender_email_key("alice@example.invalid"))

    assert [item["case_id"] for item in history["items"]] == ["CASE-ALICE"]


def test_history_refuses_reusable_mask_token_without_stable_key(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.history.settings.sqlite_path", str(db_path))
    init_db()

    alice_masked = mask_text("CASE-ALICE", "alice@example.invalid")["masked_text"]
    bob_masked = mask_text("CASE-BOB", "bob@example.invalid")["masked_text"]
    assert alice_masked == bob_masked == "[MASK_EMAIL_1]"

    _insert_case(db_path, "CASE-ALICE", alice_masked, "")
    _insert_case(db_path, "CASE-BOB", bob_masked, "")

    history = get_history("[MASK_EMAIL_1]")

    assert history["items"] == []
    assert history["is_repeated"] is False


def test_init_db_backfills_sender_email_key_from_pii_token_map(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    init_db()

    masked = mask_text("CASE-ALICE", "alice@example.invalid")["masked_text"]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cases (
                case_code, channel, status, priority, sender_email_masked,
                sender_email_key, service_provider
            )
            VALUES ('CASE-ALICE', 'email', 'uj', 'normal', ?, NULL, 'ONE')
            """,
            (masked,),
        )
        conn.commit()

    init_db()

    with sqlite3.connect(db_path) as conn:
        stored_key = conn.execute(
            "SELECT sender_email_key FROM cases WHERE case_code = 'CASE-ALICE'"
        ).fetchone()[0]

    assert stored_key == sender_email_key("alice@example.invalid")
