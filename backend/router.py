from __future__ import annotations

from config.settings import settings


def get_model_profile() -> str:
    if settings.provider == "onprem":
        return f"onprem/ollama@{settings.ollama_url}"
    if settings.openai_api_key:
        return f"cloud/{settings.openai_model}"
    return f"cloud/{settings.openai_model}-no-key"


def get_embed_profile() -> str:
    from preprocessing.embedding import active_mode

    if active_mode() == "openai":
        return f"cloud/{settings.openai_embed_model}"
    return "local/deterministic-hash-v1"
