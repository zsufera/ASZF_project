from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_MANDATORY_REFS_PATH = Path("config/mandatory_refs.yaml")


def load_mandatory_refs(path: Path = DEFAULT_MANDATORY_REFS_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    refs = payload.get("mandatory_by_category", {})
    return {str(category): list(values or []) for category, values in refs.items()}


def build_policy_map(
    category: str,
    chunks: list[dict[str, Any]],
    mandatory_refs: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    refs_by_category = mandatory_refs if mandatory_refs is not None else load_mandatory_refs()
    required_refs = refs_by_category.get(category, [])
    policy_items = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "dok_tipus": chunk.get("dok_tipus"),
            "paragrafus": chunk.get("paragrafus") or chunk.get("paragrafus_szam"),
            "idezet": chunk.get("quote", ""),
            "kozertheto_magyarazat": f"A forrás alapján ez a rész releváns a(z) {category} ügyhöz.",
            "dok_cim": chunk.get("dok_cim"),
            "oldalszam": chunk.get("oldalszam"),
            "score": chunk.get("score"),
        }
        for chunk in chunks
    ]
    missing_mandatory = required_refs if required_refs and not policy_items else []
    return {
        "policy_items": policy_items,
        "mandatory_refs": required_refs,
        "missing_mandatory": missing_mandatory,
    }
