from config.settings import Settings


def test_settings_have_local_qdrant_defaults():
    s = Settings()
    assert s.qdrant_mode == "local"
    assert s.qdrant_path == "data/qdrant_local"
    assert s.openai_embed_dim is None


def test_openai_embed_dim_parsed_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_EMBED_DIM", "1024")
    # Settings reads env at instantiation via the field defaults; re-import fresh
    import importlib
    import config.settings as settings_module

    importlib.reload(settings_module)
    assert settings_module.Settings().openai_embed_dim == 1024
    monkeypatch.delenv("OPENAI_EMBED_DIM", raising=False)
    importlib.reload(settings_module)
