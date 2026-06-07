from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.audit_service import load_retention_config
from config.settings import settings


def purge_expired_records(dry_run: bool = True) -> dict[str, Any]:
    config = load_retention_config()
    if not config.get("auto_purge_enabled") and not dry_run:
        return {"purged": False, "reason": "auto_purge_enabled=false", "dry_run": dry_run}

    now = datetime.now(timezone.utc)
    audit_days = int(config.get("audit_events_days", 365))
    pii_days = int(config.get("pii_token_map_days", 30))
    audit_cutoff = (now - timedelta(days=audit_days)).isoformat()
    pii_cutoff = (now - timedelta(days=pii_days)).isoformat()

    with sqlite3.connect(settings.sqlite_path) as conn:
        audit_candidates = conn.execute(
            "SELECT COUNT(*) FROM audit_events WHERE created_at < ?",
            (audit_cutoff,),
        ).fetchone()[0]
        pii_candidates = conn.execute(
            "SELECT COUNT(*) FROM pii_token_map WHERE created_at < ?",
            (pii_cutoff,),
        ).fetchone()[0]

        if dry_run:
            return {
                "dry_run": True,
                "audit_events_candidates": audit_candidates,
                "pii_token_map_candidates": pii_candidates,
                "audit_cutoff": audit_cutoff,
                "pii_cutoff": pii_cutoff,
            }

        conn.execute("DELETE FROM audit_events WHERE created_at < ?", (audit_cutoff,))
        conn.execute("DELETE FROM pii_token_map WHERE created_at < ?", (pii_cutoff,))
        conn.commit()

    return {
        "dry_run": False,
        "purged_audit_events": audit_candidates,
        "purged_pii_tokens": pii_candidates,
    }
