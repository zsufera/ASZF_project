from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_MANDATORY_REFS_PATH = Path("config/mandatory_refs.yaml")


def _mandatory_entry_label(entry: Any) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return str(entry.get("label") or entry.get("chunk_id") or "").strip()
    return ""


def load_mandatory_entries(path: Path = DEFAULT_MANDATORY_REFS_PATH) -> dict[str, list[dict[str, str]]]:
    """category -> [{label, chunk_id, paragrafus}] — a kötelező hivatkozások jelenlét-ellenőrzéséhez.

    A label a megjelenítéshez kell, a chunk_id/paragrafus pedig ahhoz, hogy meg tudjuk
    állapítani, az adott kötelező forrás TÉNYLEGESEN szerepel-e a visszakeresett források között.
    """
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    refs = payload.get("mandatory_by_category", {})
    result: dict[str, list[dict[str, str]]] = {}
    for category, values in refs.items():
        entries: list[dict[str, str]] = []
        for entry in (values or []):
            label = _mandatory_entry_label(entry)
            if not label:
                continue
            if isinstance(entry, dict):
                entries.append({
                    "label": label,
                    "chunk_id": str(entry.get("chunk_id") or ""),
                    "paragrafus": str(entry.get("paragrafus") or ""),
                })
            else:
                entries.append({"label": label, "chunk_id": "", "paragrafus": ""})
        result[str(category)] = entries
    return result


def load_mandatory_refs(path: Path = DEFAULT_MANDATORY_REFS_PATH) -> dict[str, list[str]]:
    """Visszafelé-kompatibilis: category -> [label] (a megjelenítéshez)."""
    return {category: [entry["label"] for entry in entries] for category, entries in load_mandatory_entries(path).items()}


def build_policy_map(
    category: str,
    chunks: list[dict[str, Any]],
    mandatory_entries: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, Any]:
    entries = (
        mandatory_entries.get(category, [])
        if mandatory_entries is not None
        else load_mandatory_entries().get(category, [])
    )
    required_refs = [entry["label"] for entry in entries if entry.get("label")]
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

    # Egy kötelező hivatkozás akkor "jelen van", ha a chunk_id-ja VAGY a paragrafusa
    # szerepel a visszakeresett források között. Korábban a logika hibás volt: bármilyen
    # forrás jelenléte "teljesítettnek" számította a kötelezőt, akkor is, ha a konkrét
    # kötelező § nem jött vissza.
    present_chunk_ids = {str(item.get("chunk_id")) for item in policy_items if item.get("chunk_id")}
    present_paragrafus = {str(item.get("paragrafus")) for item in policy_items if item.get("paragrafus")}
    missing_mandatory = [
        entry["label"]
        for entry in entries
        if entry.get("label")
        and (entry.get("chunk_id") or entry.get("paragrafus"))  # csak ellenőrizhető bejegyzés
        and str(entry.get("chunk_id")) not in present_chunk_ids
        and str(entry.get("paragrafus")) not in present_paragrafus
    ]

    return {
        "policy_items": policy_items,
        "mandatory_refs": required_refs,
        "missing_mandatory": missing_mandatory,
    }
