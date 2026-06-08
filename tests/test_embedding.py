import pytest

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


def test_openai_embed_uses_client_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_model", "text-embedding-3-large")
    monkeypatch.setattr(settings, "openai_embed_dim", 4)
    monkeypatch.setattr(emb, "EMBED_CACHE_PATH", tmp_path / "cache.db")

    calls = {"count": 0}

    def fake_embed(texts):
        calls["count"] += 1
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    monkeypatch.setattr(emb, "_openai_embed", fake_embed)

    first = emb.embed_documents(["alpha", "beta"])
    assert calls["count"] == 1
    assert len(first) == 2
    assert first[0][0] == pytest.approx(0.1, rel=1e-4)

    # Second call: both texts cached, no new API call.
    second = emb.embed_documents(["alpha", "beta"])
    assert calls["count"] == 1
    assert second[1][3] == pytest.approx(0.4, rel=1e-4)


def test_openai_partial_cache_only_embeds_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_dim", 4)
    monkeypatch.setattr(emb, "EMBED_CACHE_PATH", tmp_path / "cache.db")

    sent = []

    def fake_embed(texts):
        sent.append(list(texts))
        return [[0.5, 0.5, 0.5, 0.5] for _ in texts]

    monkeypatch.setattr(emb, "_openai_embed", fake_embed)

    emb.embed_documents(["alpha"])
    emb.embed_documents(["alpha", "gamma"])
    # First call embedded ["alpha"], second only ["gamma"].
    assert sent == [["alpha"], ["gamma"]]
