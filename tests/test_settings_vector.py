from config.settings import Settings


def test_settings_have_local_qdrant_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_EMBED_DIM", raising=False)
    s = Settings()
    assert s.qdrant_mode == "local"
    assert s.qdrant_path == "data/qdrant_local"
    assert s.openai_embed_dim is None


def test_settings_have_llm_defaults():
    s = Settings()
    assert s.llm_enabled is True
    assert s.openai_temperature == 0.2


def test_dotenv_file_is_loaded(tmp_path):
    # Run in a clean subprocess so loading a temp .env does not pollute the
    # parent test process (which may already have a real .env loaded).
    import os
    import subprocess
    import sys

    (tmp_path / ".env").write_text("OPENAI_MODEL=gpt-from-dotenv\n", encoding="utf-8")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_MODEL"}
    env["PYTHONPATH"] = repo_root

    result = subprocess.run(
        [sys.executable, "-c", "from config.settings import settings; print(settings.openai_model)"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "gpt-from-dotenv", result.stderr


def test_openai_embed_dim_parsed_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_EMBED_DIM", "1024")
    # Settings reads env at instantiation via the field defaults; re-import fresh
    import importlib
    import config.settings as settings_module

    importlib.reload(settings_module)
    assert settings_module.Settings().openai_embed_dim == 1024
    monkeypatch.delenv("OPENAI_EMBED_DIM", raising=False)
    importlib.reload(settings_module)
