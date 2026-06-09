import backend.query_rewrite as qr
from backend.query_rewrite import rewrite_query
from config.settings import settings


def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")


def test_rewrite_query_fallback_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    q = rewrite_query("Fel szeretném mondani a szerződésemet", "szerzodesfelmondas_modositas")
    assert "felmond" in q.lower()      # kategória-kulcsszó bekerül
    assert "szerződésemet" in q         # az eredeti üzenet is megmarad


def test_rewrite_query_llm_path(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(qr, "chat_json", lambda s, u: {"query": "szerződés felmondása hűségidő kötbér"})
    q = rewrite_query("Fel szeretném mondani a vezetékes szerződésemet a hűségidő lejárata előtt", "szerzodesfelmondas_modositas")
    assert q == "szerződés felmondása hűségidő kötbér"


def test_rewrite_query_empty_llm_falls_back(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(qr, "chat_json", lambda s, u: {"query": ""})
    q = rewrite_query("üzenet", "szamlazas")
    assert "száml" in q.lower()


def test_rewrite_query_llm_exception_falls_back(monkeypatch):
    _enable_llm(monkeypatch)
    def _boom(s, u):
        raise RuntimeError("api down")
    monkeypatch.setattr(qr, "chat_json", _boom)
    q = rewrite_query("üzenet", "lefedettseg")
    assert "lefedett" in q.lower()
