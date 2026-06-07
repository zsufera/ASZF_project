from __future__ import annotations

from typing import Any


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


def classify_message(message_text_masked: str, history_summary_masked: str | None = None) -> dict[str, Any]:
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
