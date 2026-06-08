"""Regressziós tesztek az agentic/LLM/RAG bug-fixekhez."""
import agent.nodes as nodes
import backend.classify as classify_mod
from config.settings import settings


def test_detect_lang_type_hungarian_with_english_word():
    # Magyar e-mail angol szóval ("please") + magyar ékezet → maradjon HU (nincs fals EN).
    state = {"case_id": "c", "input_text": "Kérem, please segítsenek a számlámmal.", "timeline": []}
    out = nodes.detect_lang_type(state)
    assert out["lang_type"]["nyelv"] == "hu"


def test_detect_lang_type_english_without_accents():
    state = {"case_id": "c", "input_text": "Dear team, please check my invoice. Regards.", "timeline": []}
    out = nodes.detect_lang_type(state)
    assert out["lang_type"]["nyelv"] == "en"


def test_prepare_unmask_strips_source_markers():
    # A jóváhagyásra előkészített (ügyfél-felé mutató) szövegből eltűnnek a [Sn] jelölők.
    state = {
        "case_id": "CASE-NOPII",
        "draft": {"subject": "Tárgy [S1]", "body_masked": "Szöveg [S1] és [S2]."},
        "timeline": [],
    }
    out = nodes.prepare_unmask(state)
    preview = out["draft_preview_unmasked"]
    assert "[S1]" not in preview["body_unmasked"]
    assert "[S2]" not in preview["body_unmasked"]
    assert "[S1]" not in preview["subject_unmasked"]


def test_classify_normalizes_spaced_category(monkeypatch):
    # A modell szóközös kategóriát ad az aláhúzós whitelist-forma helyett → ne essen fallbackre.
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(
        classify_mod,
        "chat_json",
        lambda s, u: {"fo_kategoria": "hibabejelentés szolgáltatáskiesés", "konfidencia": 0.8},
    )
    res = classify_mod.classify_message("nincs internet")
    assert res["category"] == "hibabejelentes_szolgaltataskieses"
    assert res["classify_mode"] == "llm"


def test_escalation_node_no_duplicate_repeat_reason():
    # is_repeated esetén csak a "ismetlod_panasz" jelenik meg, nincs duplikált "ismetlodo_panasz".
    state = {
        "case_id": "c",
        "input_text": "ismét írok",
        "classification": {"category": "szamlazas", "confidence": 0.9, "is_repeated": True},
        "policy_map": {"policy_items": [{"chunk_id": "x"}], "missing_mandatory": []},
        "lang_type": {"tipus": "panasz"},
        "timeline": [],
    }
    out = nodes.escalation_node(state)
    reasons = out["escalation"]["reasons"]
    assert "ismetlodo_panasz" not in reasons
    assert "ismetlod_panasz" in reasons
