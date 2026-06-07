from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

from backend.masking import mask_text


def _estimate_confidence(text: str) -> float:
    if not text.strip():
        return 0.0
    letters = len(re.findall(r"[A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű]", text))
    weird = text.count("\ufffd")
    ratio = letters / max(len(text), 1)
    penalty = min(0.4, weird * 0.02)
    return round(max(0.0, min(1.0, ratio - penalty)), 2)


def _low_confidence_spans(text: str) -> list[dict[str, int | str]]:
    spans: list[dict[str, int | str]] = []
    for match in re.finditer(r"\S+", text):
        token = match.group(0)
        if "\ufffd" in token:
            spans.append({"start": match.start(), "end": match.end(), "text": token})
    if not spans and _estimate_confidence(text) < 0.55:
        spans.append({"start": 0, "end": min(len(text), 120), "text": text[:120]})
    return spans[:20]


def extract_pdf_text(pdf_path: Path) -> str:
    parts: list[str] = []
    with fitz.open(pdf_path) as document:
        for page in document:
            parts.append(page.get_text("text"))
    return "\n".join(parts).strip()


def run_ocr(case_id: str, pdf_path: Path) -> dict[str, Any]:
    with fitz.open(pdf_path) as document:
        page_count = len(document)
        raw_text = "\n".join(page.get_text("text") for page in document).strip()
    confidence = _estimate_confidence(raw_text)
    masked = mask_text(case_id, raw_text)
    return {
        "ocr_text_masked": masked["masked_text"],
        "ocr_confidence": confidence,
        "low_conf_spans": _low_confidence_spans(raw_text),
        "page_count": page_count,
        "token_count": masked["token_count"],
    }
