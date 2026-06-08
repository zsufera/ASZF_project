import backend.classify as classify
from config.settings import settings


def test_classify_falls_back_to_rule_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    result = classify.classify_message("Problémám van a számlázással.")
    assert result["category"] == "szamlazas"
    assert result["classify_mode"] == "rule"


def test_classify_uses_llm_and_maps_display_category(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda system, user: {"fo_kategoria": "díjemelés", "konfidencia": 0.88, "tobb_jelolt": []},
    )
    result = classify.classify_message("A díjemelést kifogásolom.")
    assert result["category"] == "dijemeles"
    assert result["classify_mode"] == "llm"
    assert result["confidence"] == 0.88


def test_classify_falls_back_on_invalid_category(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(classify, "chat_json", lambda system, user: {"fo_kategoria": "nonsense"})
    result = classify.classify_message("Problémám van a számlázással.")
    assert result["category"] == "szamlazas"
    assert result["classify_mode"] == "rule"
