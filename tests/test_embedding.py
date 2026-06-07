import preprocessing.embedding as emb
from config.settings import settings


def test_deterministic_mode_when_no_key(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert emb.active_mode() == "deterministic"
    assert emb.vector_size() == 64

    vectors = emb.embed_documents(["számlázási kifogás"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 64


def test_onprem_provider_is_deterministic(monkeypatch):
    monkeypatch.setattr(settings, "provider", "onprem")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    assert emb.active_mode() == "deterministic"


def test_openai_mode_detection(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_dim", None)
    assert emb.active_mode() == "openai"
    assert emb.vector_size() == 3072
