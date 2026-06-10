# Benchmark Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hackathon-értékelő benchmark négy maradék, kóddal megfogható tételének lezárása: a deprecated `build_draft()` út törlése, Pydantic-alapú LLM-kimenet validáció, adatosztályozási dokumentáció, és friss demó/eval artefaktumok generálása.

**Architecture:** A változtatások a meglévő mintákat követik: minden LLM-hívás a `backend/llm.py::chat_json` határon megy át, hiba esetén determinisztikus fallback fut (`*_mode` mezővel jelezve). Az új Pydantic validáció a meglévő `try/except → fallback` szerkezeten BELÜL fut, így a validációs hiba automatikusan a fallback-útra terel. A `build_draft()` törlése után az egyetlen aktív generálási út a `synthesize_answer()`, a determinisztikus fallback a `build_draft_template()`.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest. Windows/PowerShell környezet.

---

## Végrehajtási környezet — KÖTELEZŐ tudnivalók

- **Platform: Windows, PowerShell.** NE használj `&&` láncolást — külön parancsok vagy `;` kell.
- **Munkakönyvtár:** `C:\source\jogos_a_kerdes\jogos_a_kerdes`
- **Git:** Ne commitolj közvetlenül `main`-re. A terv első lépése branch létrehozása. Commit trailer kötelező: `Co-Authored-By: Claude <noreply@anthropic.com>`
- **Teszt-baseline:** a teljes suite futtatásakor `1 failed, 256 passed, 19 deselected` a kiindulási állapot. Az 1 bukó teszt (`tests/test_tier3_frontend_contracts.py::test_draft_power_editing_contract`) **előzetesen létező hiba**, NEM a te dolgod javítani. Siker = továbbra is csak ez az egy bukik.
- **Hermetikus tesztkörnyezet:** a `tests/conftest.py` offline OpenAI-környezetet kényszerít. LLM-utat tesztelni csak monkeypatch-csel lehet: `monkeypatch.setattr(settings, "openai_api_key", "sk-test")` + az érintett modul `chat_json` függvényének stubolása (NEM a `backend.llm.chat_json`-é, hanem a modulba importált referenciáé, pl. `monkeypatch.setattr(classify, "chat_json", ...)`).
- **Teljes tesztfuttatás:** `python -m pytest tests/ -q` (kb. 80 másodperc).

---

### Task 0: Branch létrehozása

- [ ] **Step 1: Hozd létre és váltsd át a munkabranchet**

```powershell
git checkout -b benchmark-remediation
```

Expected: `Switched to a new branch 'benchmark-remediation'`

---

### Task 1: Deprecated `build_draft()` út eltávolítása

A `backend/draft.py`-ban két párhuzamos draft-generáló út él: a deprecated `build_draft()` (LLM + `GENERATE_SYSTEM` prompt, `DeprecationWarning`-gal) és az aktív `synthesize_answer()`. A deprecated utat töröljük; a `build_draft_template()` determinisztikus fallback-builder MARAD, mert a `synthesize_answer()` és a sablon-út használja.

**Files:**
- Modify: `backend/draft.py` (a `build_draft` függvény az 277. sor körül kezdődik; `GENERATE_SYSTEM` az 52. sorban; `import warnings` az 5. sor körül)
- Modify: `tests/test_draft.py` (teljes újraírás — 5 tesztből 2 marad, átírva `build_draft_template`-re)
- Modify: `tests/test_codebase_simplification_contracts.py` (a `test_legacy_build_draft_is_explicitly_deprecated_wrapper` teszt cseréje, 72–84. sor)
- Delete: `prompts/draft_generate.txt`
- Modify: `docs/specs/AGENT_WORKFLOW.md` (a `draft_generate.txt` sor törlése a prompt-táblázatból)

- [ ] **Step 1: Írd át a `tests/test_draft.py`-t a cél-állapotra (failing tesztek)**

Cseréld le a `tests/test_draft.py` TELJES tartalmát erre:

```python
import backend.draft as draft
from backend.draft import build_draft_template


POLICY_MAP = {
    "policy_items": [
        {
            "chunk_id": "one-3-1",
            "dok_tipus": "ÁSZF",
            "paragrafus": "3.1",
            "idezet": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            "kozertheto_magyarazat": "A forrás alapján ez a rész releváns a(z) szamlazas ügyhöz.",
            "dok_cim": "ONE ÁSZF",
            "oldalszam": 12,
            "score": 1.0,
        }
    ],
    "mandatory_refs": [],
    "missing_mandatory": [],
}


def test_build_draft_template_hitl_uses_policy_sources_without_disclaimer() -> None:
    result = build_draft_template(
        case_id="CASE-1",
        category="szamlazas",
        output_mode="hitl",
        policy_map=POLICY_MAP,
        actions=[],
    )

    assert result["subject"] == "Válaszjavaslat szamlazas ügyben"
    assert "A számlázási kifogást az ügyfélszolgálat kivizsgálja." in result["body_masked"]
    assert result["citations"] == ["one-3-1"]
    assert result["disclaimer_applied"] is False
    assert "Tisztelt Ügyfelünk!" in result["body_masked"]


def test_build_draft_template_automata_adds_disclaimer() -> None:
    result = build_draft_template(
        case_id="CASE-1",
        category="szamlazas",
        output_mode="automata",
        policy_map=POLICY_MAP,
        actions=[],
        disclaimer_text="Automata disclaimer.",
    )

    assert result["disclaimer_applied"] is True
    assert "Automata disclaimer." in result["body_masked"]


def test_deprecated_build_draft_is_removed() -> None:
    assert not hasattr(draft, "build_draft")
    assert not hasattr(draft, "GENERATE_SYSTEM")
```

- [ ] **Step 2: Cseréld le a contract tesztet a `tests/test_codebase_simplification_contracts.py`-ban**

A fájl 72–84. sorában lévő `test_legacy_build_draft_is_explicitly_deprecated_wrapper` függvényt (a `with warnings.catch_warnings...` blokkal együtt) cseréld erre:

```python
def test_legacy_build_draft_is_removed() -> None:
    assert not hasattr(draft, "build_draft")
```

Ezután ellenőrizd, hogy a fájlban máshol használatos-e a `warnings` modul:

```powershell
Select-String -Path tests\test_codebase_simplification_contracts.py -Pattern "warnings"
```

Ha a cserélt teszten kívül nincs más találat, töröld az `import warnings` sort a fájl tetejéről.

- [ ] **Step 3: Futtasd a teszteket — bukniuk kell**

```powershell
python -m pytest tests/test_draft.py tests/test_codebase_simplification_contracts.py -q
```

Expected: FAIL — `test_deprecated_build_draft_is_removed` és `test_legacy_build_draft_is_removed` bukik, mert a `build_draft` még létezik.

- [ ] **Step 4: Töröld a deprecated kódot a `backend/draft.py`-ból**

Három törlés:

1. Töröld az `import warnings` sort (a fájl tetején, az 5. sor körül).
2. Töröld a `GENERATE_SYSTEM = load_prompt("draft_generate")` sort (52. sor körül).
3. Töröld a TELJES `build_draft` függvényt — a `def build_draft(` sortól (277. sor körül) a fájl végéig tartó blokkot. A függvény így kezdődik:

```python
def build_draft(
    case_id: str,
    category: str,
    output_mode: str,
    policy_map: dict[str, Any],
    actions: list[dict[str, Any]],
    disclaimer_text: str | None = None,
) -> dict[str, Any]:
    warnings.warn(
        "build_draft() is deprecated; active answer generation uses synthesize_answer().",
        ...
```

FONTOS: a `build_draft_template`, `synthesize_answer`, `strip_source_markers`, `ensure_disclaimer`, `load_disclaimer`, `_build_sources`, `_insufficient_result`, `_template_synthesis_result` függvények és a `SYNTH_SYSTEM` konstans MARADNAK.

- [ ] **Step 5: Töröld a hozzá tartozó prompt fájlt**

```powershell
git rm prompts/draft_generate.txt
```

- [ ] **Step 6: Frissítsd az AGENT_WORKFLOW.md prompt-táblázatát**

A `docs/specs/AGENT_WORKFLOW.md` fájlban töröld ezt a táblázatsort:

```
| `prompts/draft_generate.txt` | `backend/draft.py` (deprecated) |
```

- [ ] **Step 7: Futtasd a célzott teszteket — most már zöldnek kell lenniük**

```powershell
python -m pytest tests/test_draft.py tests/test_codebase_simplification_contracts.py -q
```

Expected: PASS (minden teszt zöld).

- [ ] **Step 8: Futtasd a TELJES tesztkészletet**

```powershell
python -m pytest tests/ -q
```

Expected: `1 failed, 254 passed` (a test_draft.py 5 tesztjéből 3 lett, a contract teszt 1:1 cserélődött; az 1 bukó a fent dokumentált pre-existing `test_draft_power_editing_contract`). A pontos szám nem kritikus — a lényeg: KIZÁRÓLAG a pre-existing teszt bukhat. Ha BÁRMI MÁS bukik, vizsgáld meg — valószínűleg egy nem észlelt `build_draft` import maradt. Keresés: `Select-String -Path backend\*.py,agent\**\*.py,tests\*.py -Pattern "build_draft\b"` — csak `build_draft_template` találatok lehetnek.

- [ ] **Step 9: Commit**

```powershell
git add backend/draft.py tests/test_draft.py tests/test_codebase_simplification_contracts.py docs/specs/AGENT_WORKFLOW.md
git commit -m @'
refactor: remove deprecated build_draft() path

A synthesize_answer() az egyetlen aktív LLM draft-út; a determinisztikus
fallback a build_draft_template(). A GENERATE_SYSTEM prompt és a
draft_generate.txt törölve.

Co-Authored-By: Claude <noreply@anthropic.com>
'@
```

(A `git rm prompts/draft_generate.txt` már stage-elte a törlést, a commit tartalmazza.)

---

### Task 2: LLM-kimenet Pydantic validáció

A `chat_json()` nyers `dict`-et ad vissza; a hívó modulok ad-hoc `data.get(...)` hívásokkal olvassák. Pydantic modelleket vezetünk be minden LLM-választípusra. A validáció a meglévő `try/except` blokkokon BELÜL fut: validációs hiba (`pydantic.ValidationError`, ami `Exception` leszármazott) → a meglévő `except Exception` ág elkapja → `logger.exception` + determinisztikus fallback. A viselkedés tehát nem változik, csak a hibás LLM-kimenet detektálása lesz szigorúbb és explicit.

**Files:**
- Create: `backend/llm_schemas.py`
- Modify: `backend/classify.py` (a `classify_message` try-blokkja)
- Modify: `backend/draft.py` (a `synthesize_answer` try-blokkja)
- Modify: `backend/verify.py` (az `llm_verify_grounding` try-blokkja)
- Modify: `backend/escalation.py` (az `llm_escalation_suggestion` try-blokkja)
- Modify: `backend/query_rewrite.py` (a `rewrite_query` try-blokkja)
- Test: `tests/test_llm_output_validation.py` (új fájl)

- [ ] **Step 1: Írd meg a failing teszteket**

Hozd létre a `tests/test_llm_output_validation.py` fájlt ezzel a tartalommal:

```python
"""Hibás típusú LLM-kimenet → determinisztikus fallback (Pydantic validáció)."""
import backend.classify as classify
import backend.draft as draft
import backend.escalation as escalation
import backend.query_rewrite as query_rewrite
from config.settings import settings


def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")


def test_classify_invalid_confidence_type_falls_back_to_rule(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda system, user: {"fo_kategoria": "szamlazas", "konfidencia": "magas"},
    )
    result = classify.classify_message("Számlázási kifogásom van.")
    assert result["classify_mode"] == "rule"


def test_synthesize_invalid_sources_type_falls_back_to_template(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        draft,
        "chat_json",
        lambda system, user: {"valasz": "Válasz [S1]", "felhasznalt_forrasok": "S1"},
    )
    policy_map = {
        "policy_items": [
            {"chunk_id": "one-3-1", "idezet": "A kifogást kivizsgáljuk."}
        ],
        "missing_mandatory": [],
    }
    result = draft.synthesize_answer(
        case_id="c1", category="szamlazas", channel="email",
        output_mode="hitl", policy_map=policy_map, actions=[],
    )
    assert result["generation_mode"] == "template"


def test_escalation_invalid_okok_type_is_ignored(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        escalation,
        "chat_json",
        lambda system, user: {"eszkalacio": True, "okok": 42},
    )
    result = escalation.llm_escalation_suggestion(
        text_masked="t", category="szamlazas", confidence=0.9, policy_coverage=True
    )
    assert result == {"suggested": False, "okok": []}


def test_query_rewrite_invalid_query_type_falls_back(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        query_rewrite,
        "chat_json",
        lambda system, user: {"query": ["nem", "string"]},
    )
    result = query_rewrite.rewrite_query("fel akarom mondani", "szerzodesfelmondas_modositas")
    assert "szerződés felmondása" in result


def test_valid_llm_output_still_works(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        classify,
        "chat_json",
        lambda system, user: {
            "fo_kategoria": "szamlazas",
            "altipus": None,
            "tobb_jelolt": [{"kategoria": "szamlazas", "konfidencia": 0.9}],
            "konfidencia": 0.9,
        },
    )
    result = classify.classify_message("Számlázási kifogásom van.")
    assert result["classify_mode"] == "llm"
    assert result["category"] == "szamlazas"
```

- [ ] **Step 2: Futtasd — az új validációs tesztek közül legalább egynek buknia kell**

```powershell
python -m pytest tests/test_llm_output_validation.py -q
```

Expected: legalább a `test_classify_invalid_confidence_type_falls_back_to_rule` FAIL-el (a jelenlegi `float("magas")` egyébként is ValueError-t dob, így lehet, hogy néhány már most zöld — ez nem baj; a cél, hogy a validáció EXPLICIT legyen, ne mellékhatás).

- [ ] **Step 3: Hozd létre a `backend/llm_schemas.py` fájlt**

```python
"""Pydantic sémák a chat_json() LLM-válaszok validálásához.

Minden LLM-hívó modul a saját try-blokkjában validálja a nyers dict-et;
pydantic.ValidationError esetén a meglévő except-ág determinisztikus
fallbackre terel (ld. .claude/skills/add-llm-call).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyCandidate(BaseModel):
    kategoria: str = ""
    konfidencia: float = 0.5


class ClassifyResponse(BaseModel):
    fo_kategoria: str = ""
    altipus: str | None = None
    tobb_jelolt: list[ClassifyCandidate] = Field(default_factory=list)
    konfidencia: float = 0.6


class SynthesizeResponse(BaseModel):
    targy: str | None = None
    valasz: str = ""
    felhasznalt_forrasok: list[str] = Field(default_factory=list)
    elegtelen_fedezet: bool = False


class VerifyResponse(BaseModel):
    nem_megalapozott: list[str] = Field(default_factory=list)
    nem_megalapozott_chunk_idk: list[str] = Field(default_factory=list)


class EscalationResponse(BaseModel):
    eszkalacio: bool = False
    okok: list[str] = Field(default_factory=list)


class QueryRewriteResponse(BaseModel):
    query: str = ""
```

- [ ] **Step 4: Vezesd át a validációt a `backend/classify.py`-ba**

A `classify_message` try-blokkjában cseréld le a `data = chat_json(CLASSIFY_SYSTEM, user)` utáni feldolgozást. A jelenlegi kód:

```python
        data = chat_json(CLASSIFY_SYSTEM, user)
        # A modell visszaadhatja a kategóriát szóközzel ("hibabejelentés szolgáltatáskiesés")
        # az aláhúzós whitelist-forma helyett — normalizáljuk, hogy ne essen feleslegesen fallbackre.
        category = fold_text(str(data.get("fo_kategoria", ""))).strip().replace(" ", "_")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError("invalid category")
        confidence = float(data.get("konfidencia", 0.6))
        candidates: list[dict[str, Any]] = []
        for candidate in data.get("tobb_jelolt", []) or []:
            key = fold_text(str(candidate.get("kategoria", "")))
            if key in ALLOWED_CATEGORIES:
                candidates.append({"category": key, "confidence": float(candidate.get("konfidencia", 0.5))})
        if not candidates:
            candidates = [{"category": category, "confidence": confidence}]
        return {
            "category": category,
            "subtype": data.get("altipus"),
            "confidence": confidence,
            "candidates": candidates,
            "is_repeated": rule["is_repeated"],
            "classify_mode": "llm",
        }
```

Az új kód:

```python
        parsed = ClassifyResponse.model_validate(chat_json(CLASSIFY_SYSTEM, user))
        # A modell visszaadhatja a kategóriát szóközzel ("hibabejelentés szolgáltatáskiesés")
        # az aláhúzós whitelist-forma helyett — normalizáljuk, hogy ne essen feleslegesen fallbackre.
        category = fold_text(parsed.fo_kategoria).strip().replace(" ", "_")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError("invalid category")
        candidates: list[dict[str, Any]] = []
        for candidate in parsed.tobb_jelolt:
            key = fold_text(candidate.kategoria)
            if key in ALLOWED_CATEGORIES:
                candidates.append({"category": key, "confidence": candidate.konfidencia})
        if not candidates:
            candidates = [{"category": category, "confidence": parsed.konfidencia}]
        return {
            "category": category,
            "subtype": parsed.altipus,
            "confidence": parsed.konfidencia,
            "candidates": candidates,
            "is_repeated": rule["is_repeated"],
            "classify_mode": "llm",
        }
```

És a fájl tetején az importokhoz add hozzá:

```python
from backend.llm_schemas import ClassifyResponse
```

- [ ] **Step 5: Vezesd át a validációt a `backend/draft.py` `synthesize_answer` függvényébe**

A try-blokkban a `data = chat_json(SYNTH_SYSTEM, user)` utáni rész jelenlegi formája:

```python
        data = chat_json(SYNTH_SYSTEM, user)
        if data.get("elegtelen_fedezet"):
            return _insufficient_result(fmt, category, sources)
        body = str(data.get("valasz", "")).strip()
```

Új forma:

```python
        parsed = SynthesizeResponse.model_validate(chat_json(SYNTH_SYSTEM, user))
        if parsed.elegtelen_fedezet:
            return _insufficient_result(fmt, category, sources)
        body = parsed.valasz.strip()
```

Lejjebb ugyanebben a blokkban:

```python
        used_refs = {r for r in (data.get("felhasznalt_forrasok") or []) if r in valid_refs}
```

→

```python
        used_refs = {r for r in parsed.felhasznalt_forrasok if r in valid_refs}
```

És:

```python
        subject = str(
            data.get("targy")
            or (f"Válaszjavaslat {category} ügyben" if fmt == "email" else f"Copilot jegyzet – {category}")
        )
```

→

```python
        subject = parsed.targy or (
            f"Válaszjavaslat {category} ügyben" if fmt == "email" else f"Copilot jegyzet – {category}"
        )
```

Import a fájl tetejére:

```python
from backend.llm_schemas import SynthesizeResponse
```

- [ ] **Step 6: Vezesd át a validációt a `backend/verify.py` `llm_verify_grounding` függvényébe**

Jelenlegi:

```python
        data = chat_json(VERIFY_SYSTEM, user)
        raw = data.get("nem_megalapozott") or data.get("nem_megalapozott_chunk_idk") or []
        return {str(x) for x in raw if str(x) in chunk_by_id}
```

Új:

```python
        parsed = VerifyResponse.model_validate(chat_json(VERIFY_SYSTEM, user))
        raw = parsed.nem_megalapozott or parsed.nem_megalapozott_chunk_idk
        return {str(x) for x in raw if str(x) in chunk_by_id}
```

Import:

```python
from backend.llm_schemas import VerifyResponse
```

- [ ] **Step 7: Vezesd át a validációt a `backend/escalation.py` `llm_escalation_suggestion` függvényébe**

Jelenlegi:

```python
        data = chat_json(ESCALATION_SYSTEM, user)
        return {"suggested": bool(data.get("eszkalacio", False)), "okok": list(data.get("okok", []))}
```

Új:

```python
        parsed = EscalationResponse.model_validate(chat_json(ESCALATION_SYSTEM, user))
        return {"suggested": parsed.eszkalacio, "okok": parsed.okok}
```

Import:

```python
from backend.llm_schemas import EscalationResponse
```

- [ ] **Step 8: Vezesd át a validációt a `backend/query_rewrite.py` `rewrite_query` függvényébe**

Jelenlegi:

```python
        data = chat_json(REWRITE_SYSTEM, user)
        query = str(data.get("query", "")).strip()
        return query or _fallback_query(text_masked, category)
```

Új:

```python
        parsed = QueryRewriteResponse.model_validate(chat_json(REWRITE_SYSTEM, user))
        query = parsed.query.strip()
        return query or _fallback_query(text_masked, category)
```

Import:

```python
from backend.llm_schemas import QueryRewriteResponse
```

- [ ] **Step 9: Futtasd az új teszteket**

```powershell
python -m pytest tests/test_llm_output_validation.py -q
```

Expected: 5 passed.

- [ ] **Step 10: Futtasd a TELJES tesztkészletet**

```powershell
python -m pytest tests/ -q
```

Expected: csak a pre-existing `test_draft_power_editing_contract` bukik. Figyelem: a meglévő LLM-tesztek (`tests/test_classify_llm.py`, `tests/test_escalation_llm.py`, `tests/test_synthesize_answer.py`) valid kimeneteket stubolnak, ezeknek változatlanul zöldnek kell lenniük. Ha valamelyik bukik, a Pydantic-modell mező-defaultjai nem fedik a stub-formát — igazítsd a MODELLT (ne a tesztet).

- [ ] **Step 11: Commit**

```powershell
git add backend/llm_schemas.py backend/classify.py backend/draft.py backend/verify.py backend/escalation.py backend/query_rewrite.py tests/test_llm_output_validation.py
git commit -m @'
feat: Pydantic validation for all LLM JSON outputs

Minden chat_json-válasz explicit sémán megy át; validációs hiba a
meglévő except-ágon determinisztikus fallbackre terel.

Co-Authored-By: Claude <noreply@anthropic.com>
'@
```

---

### Task 3: Adatosztályozási szintek dokumentálása

A benchmark `data_confidentiality_docs` tétele (1/2 pont) explicit adatosztályozási szinteket vár. A DPIA-ban van adatkategória-tábla, de osztályozási SZINTEK (és kezelési szabályok szintenként) nincsenek.

**Files:**
- Modify: `docs/governance/dpia.md` (új 2.b szekció a 2. szekció után, a 18. sor körül)
- Modify: `docs/governance/compliance_checklist.md` (egy checklist-sor pontosítása)

- [ ] **Step 1: Szúrd be az adatosztályozási szekciót a DPIA-ba**

A `docs/governance/dpia.md` fájlban a 2. szekció (`## 2. Adatkategóriák` táblázata) UTÁN, a `## 3. Adatáramlás` ELŐTT szúrd be:

```markdown
## 2.b Adatosztályozási szintek (data classification)

| Szint | Leírás | Példa | Kezelési szabály |
|-------|--------|-------|------------------|
| **Publikus** | Nyilvánosan elérhető tartalom | ÁSZF PDF-ek, szabályzat-szövegek | Korlátozás nélkül indexelhető, LLM-promptba kerülhet |
| **Belső** | Üzleti, de nem személyes adat | Eszkalációs statisztikák, eval-riportok, kategória-címkék | Repo-ban tárolható, loggolható |
| **Személyes adat (PII)** | Azonosított/azonosítható természetes személy adata | Név, email, telefonszám, ügyfélszám | KIZÁRÓLAG maszkolva hagyhatja el a rendszert; maszkolatlanul csak a `pii_token_map`-ben él |
| **Maszkolt PII** | Tokenizált helyettesítő | `[NÉV_1]`, `[EMAIL_1]` | LLM-promptba, logba, auditba, tesztbe kerülhet; visszafejtés csak RBAC-védett `/unmask` úton |
| **Hitelesítési titok** | Kulcsok, jelszavak | `OPENAI_API_KEY`, jelszó-hash | Csak `.env`-ben (gitignore alatt); repo-ba, logba SOHA |

Érvényesítés: a maszkolás (`backend/masking.py`) a pipeline ELSŐ lépése, minden downstream
modul (classify, retrieve, draft, verify, escalation) kizárólag maszkolt szöveget kap.
Kapu-teszt: `tests/test_pii_gate.py`.
```

- [ ] **Step 2: Pontosítsd a compliance checklist sorát**

A `docs/governance/compliance_checklist.md` fájlban a DPIA-ra hivatkozó sort:

```markdown
- [x] DPIA dokumentálva (`docs/governance/dpia.md`)
```

cseréld erre:

```markdown
- [x] DPIA dokumentálva, adatosztályozási szintekkel és szintenkénti kezelési szabályokkal (`docs/governance/dpia.md` 2.b szekció)
```

- [ ] **Step 3: Commit**

```powershell
git add docs/governance/dpia.md docs/governance/compliance_checklist.md
git commit -m @'
docs: add data classification levels to DPIA

Co-Authored-By: Claude <noreply@anthropic.com>
'@
```

---

### Task 4: Friss demó- és eval-artefaktumok generálása

A benchmark `demo_e2e_flow` és `demo_mock_data` tételeinél a reviewer note: "manually run the demo to confirm end-to-end flow works". A repo-ban lévő demó-riport és eval-futások 2026-06-07-iek — a mai refaktor UTÁNI friss futás egyben a refaktor helyességét is igazolja.

**Files:**
- Regenerate: `data/demo/latest_demo_report.json`
- Regenerate: `data/eval/runs/<új futás>.json` (opcionális, lásd Step 2)

- [ ] **Step 1: Futtasd a demót end-to-end**

```powershell
python -m demo
```

Expected: exit code 0, a szcenáriók lefutnak (offline, API-kulcs nélküli módban determinisztikus fallbackkel — ez is érvényes futás). Ellenőrzés:

```powershell
Get-Item data\demo\latest_demo_report.json | Select-Object LastWriteTime
```

Expected: mai dátum.

Ha a demó hibával áll le, az a Task 1/2 változtatások regressziója lehet (tipikusan: a törölt `build_draft`-ra hivatkozó kód) — vesd össze a hibaüzenetet ezekkel, javítsd, és futtasd újra.

- [ ] **Step 2: Futtasd a quality gate-et**

```powershell
python scripts/run_quality_gate.py
```

Expected: lefut és riportot ír. MEGJEGYZÉS: ha `.env`-ben nincs érvényes `OPENAI_API_KEY`, az LLM-függő KPI-k fallback-módban mérődnek — ez elfogadható; a cél a friss artefaktum és a pipeline-épség igazolása. Ha a gate küszöb-hibával bukik (nem futási hibával), azt jegyezd fel a végső összefoglalóba, de NE tekintsd a feladat blokkolójának.

- [ ] **Step 3: Commitold a friss artefaktumokat**

```powershell
git add data/demo/latest_demo_report.json data/eval/
git status
```

Nézd meg a `git status` kimenetét: csak demó/eval riport JSON-ok lehetnek staged állapotban. Ha trace-fájlok (`data/traces/*.jsonl`) is bekerültek, vedd ki őket: `git restore --staged data/traces/`.

```powershell
git commit -m @'
chore: refresh demo and eval artifacts after refactor

Friss end-to-end demó-futás a build_draft-eltávolítás és a Pydantic
LLM-validáció után.

Co-Authored-By: Claude <noreply@anthropic.com>
'@
```

---

### Task 5: Záró ellenőrzés

- [ ] **Step 1: Teljes tesztkészlet utoljára**

```powershell
python -m pytest tests/ -q
```

Expected: csak `tests/test_tier3_frontend_contracts.py::test_draft_power_editing_contract` bukik (pre-existing).

- [ ] **Step 2: Frontend épség (a backend-változások nem érintik, de olcsó ellenőrizni)**

```powershell
cd frontend
npx tsc --noEmit
cd ..
```

Expected: nincs hiba.

- [ ] **Step 3: Ellenőrizd a fájlméret-limitet (benchmark: 500 sor)**

```powershell
Get-Content backend\draft.py | Measure-Object -Line
Get-Content backend\main.py | Measure-Object -Line
Get-Content backend\case_service.py | Measure-Object -Line
```

Expected: mindhárom < 500 sor (a draft.py a build_draft törlésével ~220 sorra csökken).

- [ ] **Step 4: Összefoglaló jelentés**

Írd le a felhasználónak: mely tételek készültek el, a tesztek végső állapota, a demó/quality gate eredménye, és hogy a branch (`benchmark-remediation`) merge-re kész-e.
