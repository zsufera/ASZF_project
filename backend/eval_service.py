from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.classify import classify_message
from backend.retrieval import retrieve


DEFAULT_SAMPLE_DIR = Path("data/sample_emails")


def run_eval(sample_dir: Path = DEFAULT_SAMPLE_DIR, limit: int = 10) -> dict[str, Any]:
    emails = sorted(sample_dir.glob("email-*.json"))[:limit]
    results: list[dict[str, Any]] = []
    retrieval_hits = 0
    category_hits = 0

    for path in emails:
        payload = json.loads(path.read_text(encoding="utf-8"))
        classification = classify_message(payload.get("torzs", ""))
        retrieval = retrieve(
            query=payload.get("torzs", ""),
            service_provider=payload.get("szolgaltato"),
            limit=3,
            prefer_qdrant=False,
        )
        expected_category = payload.get("varht_kategoria")
        predicted_category = classification.get("category")
        has_chunks = bool(retrieval.get("chunks"))
        if has_chunks:
            retrieval_hits += 1
        if predicted_category == expected_category:
            category_hits += 1
        results.append(
            {
                "email_id": payload.get("email_id"),
                "expected_category": expected_category,
                "predicted_category": predicted_category,
                "retrieval_hit": has_chunks,
                "retrieval_mode": retrieval.get("retrieval_mode"),
            }
        )

    total = len(results) or 1
    return {
        "evaluated": len(results),
        "category_accuracy": round(category_hits / total, 3),
        "retrieval_support": round(retrieval_hits / total, 3),
        "results": results,
    }
