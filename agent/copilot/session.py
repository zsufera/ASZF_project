from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.timeline import timeline_entry


@dataclass
class CopilotSession:
    """State for a single Copilot turn. Subagents only receive masked text."""

    session_id: str
    message_masked: str
    history: list[dict[str, str]] = field(default_factory=list)
    classification: dict[str, Any] | None = None
    retrieval: dict[str, Any] | None = None
    customer: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None
    draft: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        *,
        step: str,
        output: dict[str, Any] | None = None,
        mode: str = "rule",
        status: str = "ok",
        counts: dict[str, Any] | None = None,
        summary: str = "",
    ) -> None:
        self.timeline.append(
            timeline_entry(
                step,
                output=output,
                mode=mode,
                status=status,
                counts=counts,
                summary=summary,
            )
        )
