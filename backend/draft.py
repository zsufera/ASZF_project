from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_DISCLAIMER_PATH = Path("config/disclaimer.yaml")


def load_disclaimer(path: Path = DEFAULT_DISCLAIMER_PATH) -> str:
    if not path.exists():
        return ""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return str(payload.get("text_hu", "")).strip()


def build_draft(
    case_id: str,
    category: str,
    output_mode: str,
    policy_map: dict[str, Any],
    actions: list[dict[str, Any]],
    disclaimer_text: str | None = None,
) -> dict[str, Any]:
    policy_items = policy_map.get("policy_items", [])
    citations = [item.get("chunk_id") for item in policy_items if item.get("chunk_id")]
    source_lines = [
        f"- {item.get('idezet', '')} (forrás: {item.get('chunk_id')})"
        for item in policy_items
        if item.get("idezet")
    ]
    action_lines = [
        f"- {action.get('tipus')}: {action.get('indok', '')}"
        for action in actions
        if action.get("tipus")
    ]

    body_parts = [
        "Tisztelt Ügyfelünk!",
        "",
        "Az ügyintézői válaszjavaslat az alábbi források alapján készült:",
        *(source_lines or ["- Nincs elegendő forrás a biztos válaszhoz."]),
    ]
    if action_lines:
        body_parts.extend(["", "Javasolt intézkedés:", *action_lines])

    if policy_map.get("missing_mandatory"):
        body_parts.extend(
            [
                "",
                "Figyelmeztetés: hiányzó kötelező behivatkozás(ok):",
                *[f"- {item}" for item in policy_map["missing_mandatory"]],
            ]
        )

    disclaimer_applied = output_mode == "automata"
    if disclaimer_applied:
        body_parts.extend(["", disclaimer_text if disclaimer_text is not None else load_disclaimer()])

    body_parts.extend(["", "Üdvözlettel,", "Ügyfélszolgálat"])

    return {
        "subject": f"Válaszjavaslat {category} ügyben",
        "body_masked": "\n".join(body_parts),
        "citations": citations,
        "disclaimer_applied": disclaimer_applied,
    }
