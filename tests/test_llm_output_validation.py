"""Hibás típusú LLM-kimenet → determinisztikus fallback (Pydantic validáció)."""
import backend.classify as classify
import backend.draft as draft
import backend.escalation as escalation
import backend.query_rewrite as query_rewrite
from config.settings import settings


def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")


def test_classify_invalid_confidence_type_falls_back_to_rule(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda system, user: {"fo_kategoria": "szamlazas", "konfidencia": "magas"},
    )
    result = classify.classify_message("Számlázási kifogásom van.")
    assert result["classify_mode"] == "rule"


def test_synthesize_invalid_sources_type_falls_back_to_template(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        draft,
        "chat_json",
        lambda system, user: {"valasz": "Válasz [S1]", "felhasznalt_forrasok": "S1"},
    )
    policy_map = {
        "policy_items": [
            {"chunk_id": "one-3-1", "idezet": "A kifogást kivizsgáljuk."}
        ],
        "missing_mandatory": [],
    }
    result = draft.synthesize_answer(
        case_id="c1", category="szamlazas", channel="email",
        output_mode="hitl", policy_map=policy_map, actions=[],
    )
    assert result["generation_mode"] == "template"


def test_escalation_invalid_okok_type_is_ignored(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        escalation,
        "chat_json",
        lambda system, user: {"eszkalacio": True, "okok": 42},
    )
    result = escalation.llm_escalation_suggestion(
        text_masked="t", category="szamlazas", confidence=0.9, policy_coverage=True
    )
    assert result == {"suggested": False, "okok": []}


def test_query_rewrite_invalid_query_type_falls_back(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        query_rewrite,
        "chat_json",
        lambda system, user: {"query": ["nem", "string"]},
    )
    result = query_rewrite.rewrite_query("fel akarom mondani", "szerzodesfelmondas_modositas")
    assert "szerződés felmondása" in result


def test_valid_llm_output_still_works(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda system, user: {
            "fo_kategoria": "szamlazas",
            "altipus": None,
            "tobb_jelolt": [{"kategoria": "szamlazas", "konfidencia": 0.9}],
            "konfidencia": 0.9,
        },
    )
    result = classify.classify_message("Számlázási kifogásom van.")
    assert result["classify_mode"] == "llm"
    assert result["category"] == "szamlazas"
