from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.router import get_model_profile
from config.settings import settings


PROMPT_VERSION = "2026.06.07"
DEFAULT_MANIFEST_PATH = Path("data/ingest_manifest.json")


def new_request_id() -> str:
    return str(uuid.uuid4())


def load_manifest_summary(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"document_count": 0, "aszf_version": None, "generated_at": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    versions = sorted(
        {
            item.get("version_hint")
            for item in payload.get("documents", [])
            if item.get("version_hint")
        },
        reverse=True,
    )
    return {
        "document_count": payload.get("document_count", 0),
        "aszf_version": versions[0] if versions else None,
        "generated_at": payload.get("generated_at"),
    }


def response_meta(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = load_manifest_summary()
    meta = {
        "request_id": new_request_id(),
        "model_profile": get_model_profile(),
        "prompt_version": PROMPT_VERSION,
        "aszf_version": manifest.get("aszf_version"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        meta.update(extra)
    return meta
