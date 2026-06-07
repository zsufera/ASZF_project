import pytest

import backend.llm as llm
from config.settings import settings


def test_llm_available_requires_key_and_enabled(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    assert llm.llm_available() is True

    monkeypatch.setattr(settings, "openai_api_key", "")
    assert llm.llm_available() is False


def test_llm_unavailable_when_disabled_or_onprem(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "provider", "onprem")
    assert llm.llm_available() is False
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", False)
    assert llm.llm_available() is False


def test_chat_json_parses_completion(monkeypatch):
    monkeypatch.setattr(llm, "_chat_completion", lambda messages: '{"a": 1, "b": "x"}')
    result = llm.chat_json("system", "user")
    assert result == {"a": 1, "b": "x"}


def test_chat_json_raises_on_bad_json(monkeypatch):
    monkeypatch.setattr(llm, "_chat_completion", lambda messages: "not json")
    with pytest.raises(ValueError):
        llm.chat_json("system", "user")
