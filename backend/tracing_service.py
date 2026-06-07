from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRACE_DIR = Path(os.getenv("TRACE_DIR", "data/traces"))
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def trace_event(
    name: str,
    payload: dict[str, Any] | None = None,
    *,
    case_id: str | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    entry = {
        "name": name,
        "case_id": case_id,
        "duration_ms": duration_ms,
        "payload": payload or {},
        "created_at": _utc_now(),
        "backend": "local_json",
        "langfuse_enabled": LANGFUSE_ENABLED,
        "langfuse_host": LANGFUSE_HOST if LANGFUSE_ENABLED else None,
    }
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = TRACE_DIR / f"trace-{day}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def list_recent_traces(limit: int = 50) -> list[dict[str, Any]]:
    if not TRACE_DIR.exists():
        return []
    files = sorted(TRACE_DIR.glob("trace-*.jsonl"), reverse=True)
    entries: list[dict[str, Any]] = []
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(entries) >= limit:
                return entries
    return entries
