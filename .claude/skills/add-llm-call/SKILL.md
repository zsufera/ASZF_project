---
name: add-llm-call
description: Use when adding or modifying an LLM-backed function in this repo (classification, drafting, escalation, verification, judging). Encodes the chat_json + deterministic-fallback + *_mode + logging idiom and the gpt-5 temperature trap and hermetic-test pattern.
---

# LLM-hívás hozzáadása (repo-idióma)

Minden LLM-hívásnak ezt a mintát kell követnie ebben a kódbázisban. Ne hívd közvetlenül az `openai` SDK-t a `backend/llm.py`-on kívül.

## A minta

```python
import logging
from backend.llm import chat_json, llm_available

logger = logging.getLogger(__name__)

SYSTEM = (
    "<rövid, parancsoló rendszerutasítás magyarul>. "
    'Válasz JSON: {"mezo": "...", ...}'   # mindig add meg a JSON-sémát a promptban
)

def my_step(text_masked: str, ...) -> dict:
    # 1) Determinisztikus alap/szabály-eredmény ELŐSZÖR (ez a fallback is)
    rule = my_step_rule(text_masked, ...)
    if not llm_available():
        rule["my_mode"] = "rule"      # *_mode mező: rule | llm | template | insufficient
        return rule
    try:
        user = f'Maszkolt bemenet:\n"""\n{text_masked}\n"""\n...'
        data = chat_json(SYSTEM, user)          # JSON-object mód, egyetlen hívás
        # 2) VALIDÁLD a kimenetet (whitelist / séma); érvénytelen → kivétel → fallback
        ...
        return {..., "my_mode": "llm"}
    except Exception:
        logger.exception("my_step LLM path failed; falling back to rules")
        rule["my_mode"] = "rule"
        return rule
```

## Kötelező szabályok
- **Csak maszkolt szöveg** mehet a promptba. A `SYSTEM_PREAMBLE` (a `chat_json` hozzáadja) a bemenetet ADAT-ként kezeli — ne írj felül injection-érzékeny utasítást.
- **Determinisztikus fallback** mindig legyen, és **`*_mode` mezővel** jelöld, melyik út futott (`classify_mode`, `generation_mode`, `escalation_mode`, `verify_mode`).
- **Ne nyeld el némán** a kivételt: `logger.exception(...)` + fallback.
- **Temperature-csapda:** a `gpt-5*` és `o1/o3/o4` modellek csak a default temperature-t fogadják el. A `_chat_completion` ezt a `_supports_custom_temperature()`-rel kezeli — **ne** adj a híváshoz feltétlen `temperature=`-t, és ne kerüld meg a `chat_json`-t.
- **Latencia:** minden LLM-hívás ~15–20s (gpt-5-mini reasoning). Lehetőleg **egy kötegelt hívás** (ne forrásonként/elemenként). Ha új hívást teszel a hot-path-ba (pl. agent pipeline), mérlegeld a +latenciát, és tedd kapcsolhatóvá env-flaggel, ha indokolt (ld. `LLM_VERIFY_ENABLED`).
- **Validáld** az LLM kimenetét (kategória-whitelist, létező citation-id, séma) — érvénytelennél esd vissza, ne propagálj.

## Teszt (TDD, hermetikus)
A `tests/conftest.py` üres OpenAI-kulcsra kényszerít. LLM-utat így tesztelj:

```python
import backend.my_module as my_module
from config.settings import settings

def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")

def test_my_step_llm(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(my_module, "chat_json", lambda s, u: {"mezo": "..."})
    res = my_module.my_step("maszkolt szöveg")
    assert res["my_mode"] == "llm"

def test_my_step_fallback_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    res = my_module.my_step("maszkolt szöveg")
    assert res["my_mode"] == "rule"
```
- **Soha** ne tesztelj szó szerinti LLM-szövegre — mezőkre, flagekre, `*_mode`-ra, citationökre asserts.
- Adj **fallback-tesztet** (LLM nélkül) és **kivétel-tesztet** (`chat_json` dob → fallback).

## Ellenőrző lista
- [ ] `chat_json` használat, JSON-séma a promptban, csak maszkolt bemenet
- [ ] determinisztikus fallback + `*_mode` mező
- [ ] `logger.exception` az except ágban
- [ ] kimenet-validáció
- [ ] LLM- és fallback-teszt (hermetikus, mockolt `chat_json`)
- [ ] nem vezettél vissza feltétlen `temperature=`-t
