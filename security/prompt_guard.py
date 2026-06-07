from __future__ import annotations

import re

INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"you\s+are\s+now", re.I),
    re.compile(r"<\s*/?\s*script", re.I),
)


def detect_prompt_injection(text: str) -> dict[str, bool | list[str]]:
    hits = [pattern.pattern for pattern in INJECTION_PATTERNS if pattern.search(text)]
    return {"detected": bool(hits), "patterns": hits}
