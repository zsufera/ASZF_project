from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_DIR = Path("data/sample_emails")


def load_question_bank(
    sample_dir: Path = DEFAULT_SAMPLE_DIR,
    limit: int | None = None,
    category: str | None = None,
    service_provider: str | None = None,
    include_edge: bool = True,
) -> list[dict[str, Any]]:
    paths = sorted(sample_dir.glob("email*.json"))
    if not include_edge:
        paths = [path for path in paths if "edge" not in path.name]

    items: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if category and payload.get("varht_kategoria") != category:
            continue
        if service_provider and payload.get("szolgaltato") != service_provider:
            continue
        payload["_source_path"] = str(path)
        items.append(payload)
        if limit and len(items) >= limit:
            break
    return items
