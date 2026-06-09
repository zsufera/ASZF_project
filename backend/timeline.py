from __future__ import annotations

from typing import Any


def timeline_entry(
    step: str,
    *,
    output: dict[str, Any] | None = None,
    mode: str = "rule",
    status: str = "ok",
    counts: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    summary: str = "",
) -> dict[str, Any]:
    """Build a timeline entry that keeps the legacy step/output shape."""
    return {
        "step": step,
        "output": output or {},
        "mode": mode,
        "status": status,
        "counts": counts or {},
        "warnings": warnings or [],
        "summary": summary,
    }
