from backend.router import get_model_profile
from config.settings import settings


def test_model_profile_no_key(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert get_model_profile().endswith("-no-key")


def test_model_profile_with_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_model", "gpt-4.1")
    assert get_model_profile() == "cloud/gpt-4.1"


def test_model_profile_no_key_when_llm_disabled(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_enabled", False)
    assert get_model_profile().endswith("-no-key")
