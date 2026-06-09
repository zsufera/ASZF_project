from __future__ import annotations

from typing import Any

from backend import llm_tasks


def classify(message_text_masked: str, history_summary_masked: str | None = None) -> dict[str, Any]:
    task = llm_tasks.classify_message_task(message_text_masked, history_summary_masked)
    result = task["result"]
    return {
        "category": result.get("category", "egyeb"),
        "subtype": result.get("subtype"),
        "confidence": result.get("confidence", 0.0),
        "candidates": result.get("candidates", []),
        "is_repeated": result.get("is_repeated", False),
        "mode": task["mode"],
    }
