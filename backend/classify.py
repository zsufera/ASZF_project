from __future__ import annotations

from typing import Any

from backend.llm import chat_json, llm_available
from preprocessing.index import fold_text


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

CLASSIFY_SYSTEM = (
    "Sorold be a panaszt a következő fix kategóriákba (egy fő + szükség esetén több jelölt): "
    "számlázás, díjemelés, hibabejelentés_szolgáltatáskiesés, szerződésfelmondás_módosítás, "
    "lefedettség, eszköz_készülék, adatvédelem, egyéb. Ha van rá jel, adj szabályzati altípust is. "
    "Vedd figyelembe a korábbi azonos-című ügyek összegzését, ha adott. "
    'Válasz JSON: {"fo_kategoria": "...", "altipus": "string|null", '
    '"tobb_jelolt": [{"kategoria": "...", "konfidencia": 0.0}], "konfidencia": 0.0}'
)


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
        data = chat_json(CLASSIFY_SYSTEM, user)
        category = fold_text(str(data.get("fo_kategoria", "")))
        if category not in ALLOWED_CATEGORIES:
            raise ValueError("invalid category")
        confidence = float(data.get("konfidencia", 0.6))
        candidates: list[dict[str, Any]] = []
        for candidate in data.get("tobb_jelolt", []) or []:
            key = fold_text(str(candidate.get("kategoria", "")))
            if key in ALLOWED_CATEGORIES:
                candidates.append({"category": key, "confidence": float(candidate.get("konfidencia", 0.5))})
        if not candidates:
            candidates = [{"category": category, "confidence": confidence}]
        return {
            "category": category,
            "subtype": data.get("altipus"),
            "confidence": confidence,
            "candidates": candidates,
            "is_repeated": rule["is_repeated"],
            "classify_mode": "llm",
        }
    except Exception:
        rule["classify_mode"] = "rule"
        return rule
