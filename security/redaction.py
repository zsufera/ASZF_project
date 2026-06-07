from __future__ import annotations

import re
from typing import Any

from backend.masking import CUSTOMER_ID_PATTERN, EMAIL_PATTERN, PHONE_PATTERN, SIM_PATTERN


REDACTED = "[REDACTED]"
SENSITIVE_KEYS = {
    "original_value",
    "subject_unmasked",
    "body_unmasked",
    "subject_unmasked_preview",
    "ocr_text_raw",
}


def redact_text(text: str) -> str:
    if not text:
        return text
    redacted = EMAIL_PATTERN.sub(REDACTED, text)
    redacted = PHONE_PATTERN.sub(REDACTED, redacted)
    redacted = SIM_PATTERN.sub(REDACTED, redacted)
    redacted = CUSTOMER_ID_PATTERN.sub(REDACTED, redacted)
    return redacted


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if key in SENSITIVE_KEYS:
                cleaned[key] = REDACTED
            else:
                cleaned[key] = redact_payload(value)
        return cleaned
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, str):
        return redact_text(payload)
    return payload
