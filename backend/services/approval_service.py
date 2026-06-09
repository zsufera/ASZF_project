from __future__ import annotations

from typing import Any

from backend.draft import strip_source_markers
from backend.masking import unmask_text


def prepare_preview(
    case_id: str,
    subject: str,
    body_masked: str,
    *,
    verify_warning: bool = False,
    escalation_required: bool = False,
    generation_mode: str = "llm",
) -> dict[str, Any]:
    ready_for_approval = (
        not verify_warning and not escalation_required and generation_mode != "insufficient"
    )
    return {
        "subject_unmasked": strip_source_markers(unmask_text(case_id, subject)),
        "body_unmasked": strip_source_markers(unmask_text(case_id, body_masked)),
        "ready_for_approval": ready_for_approval,
    }
