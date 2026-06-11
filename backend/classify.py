from __future__ import annotations

import logging
from typing import Any

from backend.llm import chat_json, llm_available, load_prompt
from backend.llm_schemas import ClassifyResponse
from preprocessing.index import fold_text

logger = logging.getLogger(__name__)


ALLOWED_CATEGORIES = {
    "szamlazas",
    "dijemeles",
    "hibabejelentes_szolgaltataskieses",
    "szerzodesfelmondas_modositas",
    "lefedettseg",
    "eszkoz_keszulek",
    "adatvedelem",
    "egyeb",
}

CLASSIFY_SYSTEM = load_prompt("classify")


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "szamlazas": ("számla", "szamla", "számlázás", "szamlazas", "számlázási", "szamlazasi"),
    "dijemeles": ("díjemelés", "dijemeles", "díjmódosítás", "dijmodositas", "áremelés", "aremelés"),
    "hibabejelentes_szolgaltataskieses": (
        "hiba",
        "hibabejelentés",
        "szolgáltatáskiesés",
        "szolgaltataskieses",
        "kimaradás",
        "nincs internet",
    ),
    "szerzodesfelmondas_modositas": ("felmondás", "felmondas", "szerződésmódosítás", "szerzodesmodositas"),
    "lefedettseg": ("lefedettség", "lefedettseg", "térerő", "terero"),
    "eszkoz_keszulek": ("készülék", "keszulek", "modem", "router", "eszköz", "eszkoz"),
    "adatvedelem": ("adatvédelem", "adatvedelem", "gdpr", "személyes adat", "szemelyes adat"),
}


def normalize(text: str) -> str:
    return text.lower()


def classify_message_rule(message_text_masked: str, history_summary_masked: str | None = None) -> dict[str, Any]:
    text = normalize(message_text_masked)
    scores: list[tuple[int, str]] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            scores.append((score, category))

    scores.sort(reverse=True)
    category = scores[0][1] if scores else "egyeb"
    raw_score = scores[0][0] if scores else 0
    confidence = min(0.95, 0.5 + raw_score * 0.2) if scores else 0.45
    subtype = "dijmodositas" if category == "dijemeles" else None
    history_text = normalize(history_summary_masked or "")
    is_repeated = any(term in history_text for term in ("ismétlődő", "ismetlod", "korábban", "korabban"))

    candidates = [{"category": candidate, "confidence": min(0.95, 0.5 + score * 0.2)} for score, candidate in scores[:3]]

    return {
        "category": category,
        "subtype": subtype,
        "confidence": confidence,
        "candidates": candidates,
        "is_repeated": is_repeated,
    }


def classify_message(message_text_masked: str, history_summary_masked: str | None = None) -> dict[str, Any]:
    rule = classify_message_rule(message_text_masked, history_summary_masked)
    if not llm_available():
        rule["classify_mode"] = "rule"
        return rule
    try:
        user = (
            f'Maszkolt üzenet:\n"""\n{message_text_masked}\n"""\n'
            f"Előzmény-összegzés (opcionális): {history_summary_masked or ''}"
        )
        parsed = ClassifyResponse.model_validate(chat_json(CLASSIFY_SYSTEM, user))
        # A modell visszaadhatja a kategóriát szóközzel ("hibabejelentés szolgáltatáskiesés")
        # az aláhúzós whitelist-forma helyett — normalizáljuk, hogy ne essen feleslegesen fallbackre.
        category = fold_text(parsed.fo_kategoria).strip().replace(" ", "_")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError("invalid category")
        candidates: list[dict[str, Any]] = []
        for candidate in parsed.tobb_jelolt:
            key = fold_text(candidate.kategoria)
            if key in ALLOWED_CATEGORIES:
                candidates.append({"category": key, "confidence": candidate.konfidencia})
        if not candidates:
            candidates = [{"category": category, "confidence": parsed.konfidencia}]
        return {
            "category": category,
            "subtype": parsed.altipus,
            "confidence": parsed.konfidencia,
            "candidates": candidates,
            "is_repeated": rule["is_repeated"],
            "classify_mode": "llm",
        }
    except Exception:
        logger.exception("classify_message LLM path failed; falling back to rules")
        rule["classify_mode"] = "rule"
        return rule
