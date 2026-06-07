from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Protocol

from config.settings import settings


class EmailAdapter(Protocol):
    def send_mock(self, case_id: str, subject: str, body_masked: str, actor: str | None = None) -> dict[str, Any]:
        ...


class MockEmailAdapter:
    def send_mock(
        self,
        case_id: str,
        subject: str,
        body_masked: str,
        actor: str | None = None,
    ) -> dict[str, Any]:
        with sqlite3.connect(settings.sqlite_path) as conn:
            row = conn.execute(
                "SELECT id FROM cases WHERE case_code = ?",
                (case_id,),
            ).fetchone()
            if not row:
                return {"error": "Ügy nem található", "case_id": case_id}
            case_db_id = row[0]
            sent_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO messages (case_id, direction, raw_text_masked, channel_payload)
                VALUES (?, 'outbound_mock', ?, ?)
                """,
                (
                    case_db_id,
                    body_masked,
                    json.dumps(
                        {"subject_masked": subject, "mock_sent": True, "actor": actor, "sent_at": sent_at},
                        ensure_ascii=False,
                    ),
                ),
            )
            conn.execute(
                "UPDATE cases SET status = 'lezarva', updated_at = ? WHERE id = ?",
                (sent_at, case_db_id),
            )
            conn.commit()
        return {"case_id": case_id, "mock_sent": True, "sent_at": sent_at, "adapter": "mock"}
