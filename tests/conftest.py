import pytest

from config.settings import settings


@pytest.fixture(autouse=True)
def _hermetic_openai(monkeypatch):
    """Keep the test suite offline and deterministic.

    A local `.env` may contain a real `OPENAI_API_KEY`; `config.settings` loads
    it at import time. Without this guard, any test that exercises the embedding
    or retrieval path would make real OpenAI API calls. We force an empty key
    (so `active_mode()` returns "deterministic") before every test. Tests that
    need the OpenAI path opt in explicitly by setting the key themselves and
    mocking `preprocessing.embedding._openai_embed`.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
