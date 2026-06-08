from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from backend.llm import chat_json, llm_available


MARKER_RE = re.compile(r"\[S\d+\]")


def strip_source_markers(text: str | None) -> str:
    """Eltávolítja a [Sn] forrás-jelölőket és normalizálja a felesleges szóközöket."""
    cleaned = MARKER_RE.sub("", text or "")
    cleaned = re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _build_sources(policy_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """policy_items -> rendezett, ref-indexelt gazdag forrás-objektumok."""
    sources: list[dict[str, Any]] = []
    for item in policy_items:
        if not item.get("chunk_id"):
            continue
        sources.append({
            "ref": f"S{len(sources) + 1}",
            "chunk_id": item.get("chunk_id"),
            "dok_cim": item.get("dok_cim"),
            "dok_tipus": item.get("dok_tipus"),
            "paragrafus": item.get("paragrafus"),
            "oldalszam": item.get("oldalszam"),
            "idezet": item.get("idezet", ""),
            "magyarazat": item.get("kozertheto_magyarazat"),
            "score": item.get("score"),
            "used": False,
        })
    return sources


DEFAULT_DISCLAIMER_PATH = Path("config/disclaimer.yaml")

GENERATE_SYSTEM = (
    "Írj hivatalos, udvarias magyar válaszlevelet a maszkolt adatok megtartásával. "
    "Szerkezet: tárgy, megszólítás, törzs, javasolt intézkedés, aláírás. "
    "Minden tartalmi állításhoz hivatkozz a megadott forrásokra (chunk_id). "
    "Csak a megadott forrásokra alapozz; ha nincs fedezet, jelezd és javasolj eszkalációt. "
    'Válasz JSON: {"targy": "...", "level_szoveg": "... (maszkolt)", "felhasznalt_forrasok": ["chunk_id"]}'
)


def load_disclaimer(path: Path = DEFAULT_DISCLAIMER_PATH) -> str:
    if not path.exists():
        return ""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return str(payload.get("text_hu", "")).strip()


def ensure_disclaimer(body_masked: str, output_mode: str) -> tuple[str, bool]:
    if output_mode != "automata":
        return body_masked, False
    disclaimer = load_disclaimer()
    if not disclaimer:
        return body_masked, False
    if disclaimer in body_masked:
        return body_masked, True
    return f"{body_masked.rstrip()}\n\n{disclaimer}", True


def build_draft_template(
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


def build_draft(
    case_id: str,
    category: str,
    output_mode: str,
    policy_map: dict[str, Any],
    actions: list[dict[str, Any]],
    disclaimer_text: str | None = None,
) -> dict[str, Any]:
    policy_items = policy_map.get("policy_items", [])
    if not llm_available() or not policy_items:
        result = build_draft_template(case_id, category, output_mode, policy_map, actions, disclaimer_text)
        result["generation_mode"] = "template"
        return result
    try:
        available_ids = {item.get("chunk_id") for item in policy_items if item.get("chunk_id")}
        sources_block = "\n".join(
            f"- [{item.get('chunk_id')}] \"{item.get('idezet', '')}\""
            for item in policy_items
            if item.get("idezet")
        )
        action_block = "\n".join(
            f"- {action.get('tipus')}: {action.get('indok', '')}"
            for action in actions
            if action.get("tipus")
        )
        disclaimer = disclaimer_text if disclaimer_text is not None else load_disclaimer()
        user = (
            f"Kimeneti mód: {output_mode}\n"
            f"Kategória: {category}\n"
            f"Források:\n{sources_block}\n"
            f"Javasolt intézkedés:\n{action_block or '- (nincs)'}\n"
            f"Disclaimer (ha a mód automata): {disclaimer}"
        )
        data = chat_json(GENERATE_SYSTEM, user)
        body = str(data.get("level_szoveg", "")).strip()
        if not body:
            raise ValueError("empty body")
        subject = str(data.get("targy") or f"Válaszjavaslat {category} ügyben")
        citations = [c for c in (data.get("felhasznalt_forrasok") or []) if c in available_ids]
        body, disclaimer_applied = ensure_disclaimer(body, output_mode)
        return {
            "subject": subject,
            "body_masked": body,
            "citations": citations,
            "disclaimer_applied": disclaimer_applied,
            "generation_mode": "llm",
        }
    except Exception:
        result = build_draft_template(case_id, category, output_mode, policy_map, actions, disclaimer_text)
        result["generation_mode"] = "template"
        return result
