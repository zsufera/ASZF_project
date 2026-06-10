from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from config.settings import settings

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


SYSTEM_PREAMBLE = load_prompt("preamble")


def llm_available() -> bool:
    return (
        settings.llm_enabled
        and settings.provider != "onprem"
        and bool(settings.openai_api_key)
    )


def _supports_custom_temperature(model: str) -> bool:
    """A gpt-5 család és az o-széria reasoning modellek csak a default temperature=1
    értéket fogadják el (a custom temperature 400-as hibát dob). Ezeknél nem küldünk
    explicit temperature-t, így a modell a saját default értékét használja."""
    m = (model or "").lower()
    if m.startswith("gpt-5"):
        return False
    if m.startswith(("o1", "o3", "o4")):
        return False
    return True


def _chat_completion(messages: list[dict[str, str]]) -> str:
    from openai import OpenAI

    # 90 s per call: classify + draft + verify + escalation should each finish
    # well within this; prevents silent hangs on API-side delays.
    client = OpenAI(api_key=settings.openai_api_key, timeout=90)
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    # Csak akkor küldünk explicit temperature-t, ha a modell támogatja a custom értéket.
    if _supports_custom_temperature(settings.openai_model):
        kwargs["temperature"] = settings.openai_temperature
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or "{}"


def chat_json(system: str, user: str) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": f"{SYSTEM_PREAMBLE}\n\n{system}"},
        {"role": "user", "content": user},
    ]
    raw = _chat_completion(messages)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {exc}") from exc
