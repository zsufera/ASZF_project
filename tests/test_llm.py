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


def _fake_openai(recorder):
    """Fake openai.OpenAI that records the create() kwargs and returns a JSON body."""
    class _Completions:
        def create(self, **kwargs):
            recorder.update(kwargs)
            msg = type("Msg", (), {"content": '{"ok": true}'})()
            choice = type("Choice", (), {"message": msg})()
            return type("Resp", (), {"choices": [choice]})()

    class _Client:
        def __init__(self, *args, **kwargs):
            self.chat = type("Chat", (), {"completions": _Completions()})()

    return _Client


def test_supports_custom_temperature_by_model_family():
    # gpt-4 family supports a custom temperature
    assert llm._supports_custom_temperature("gpt-4.1") is True
    assert llm._supports_custom_temperature("gpt-4o") is True
    # gpt-5 family and o-series reasoning models only allow the default temperature
    assert llm._supports_custom_temperature("gpt-5") is False
    assert llm._supports_custom_temperature("gpt-5-mini") is False
    assert llm._supports_custom_temperature("o1-mini") is False
    assert llm._supports_custom_temperature("o3") is False


def test_chat_completion_omits_temperature_for_default_only_model(monkeypatch):
    import openai
    recorder: dict = {}
    monkeypatch.setattr(openai, "OpenAI", _fake_openai(recorder))
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_model", "gpt-5-mini")
    monkeypatch.setattr(settings, "openai_temperature", 0.2)

    out = llm._chat_completion([{"role": "user", "content": "hi"}])

    assert out == '{"ok": true}'
    assert "temperature" not in recorder  # gpt-5 rejects a custom temperature
    assert recorder["model"] == "gpt-5-mini"


def test_chat_completion_includes_temperature_for_standard_model(monkeypatch):
    import openai
    recorder: dict = {}
    monkeypatch.setattr(openai, "OpenAI", _fake_openai(recorder))
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_model", "gpt-4.1")
    monkeypatch.setattr(settings, "openai_temperature", 0.2)

    llm._chat_completion([{"role": "user", "content": "hi"}])

    assert recorder["temperature"] == 0.2
