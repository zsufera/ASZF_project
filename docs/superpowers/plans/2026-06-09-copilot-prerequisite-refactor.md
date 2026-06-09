# Copilot előfeltétel-refactor ("közös varrat") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Copilot orchestrator alá eső "közös varrat" letisztítása: mode-enumok, egységes timeline-séma, központi LLM-boundary, eset-szintű service-réteg és egy golden-case regressziós háló — hogy a lineáris graph ÉS az új Copilot agent ugyanazt a stabil üzleti logikát hívja.

**Architecture:** Additív, visszafelé kompatibilis refaktor. Az enumok `str`-alapúak (a meglévő string-összehasonlítások és a JSON-szerializáció változatlanul működnek). A timeline egységes séma a meglévő `{step, output}` szuperhalmaza (a frontend nem törik). Az `llm_tasks` és a `services/` réteg a meglévő `backend/` függvényeket csomagolja, nem írja újra.

**Tech Stack:** Python 3 (FastAPI, LangGraph), pytest. Windows/PowerShell: `;` lánc, `python -m pytest`.

---

## Fájlszerkezet

- Create: `backend/modes.py` — `str`-alapú mode-enumok (egy hely a `*_mode` konstansoknak).
- Create: `backend/timeline.py` — egységes timeline-bejegyzés gyártó.
- Create: `backend/llm_tasks.py` — központi LLM-boundary, egységes `{mode, result, error}`.
- Create: `backend/services/__init__.py`
- Create: `backend/services/classification_service.py`
- Create: `backend/services/rag_service.py`
- Create: `backend/services/approval_service.py`
- Create: `tests/test_modes.py`, `tests/test_timeline.py`, `tests/test_llm_tasks.py`, `tests/test_services.py`, `tests/test_golden_cases.py`
- Modify: `agent/nodes.py` — a node-ok a service-eket és az egységes timeline-t használják (vékonyítás).

A `*.py` üzleti logika (`classify.py`, `draft.py`, `retrieval.py`, `escalation.py`, `verify.py`, `policy_map.py`, `query_rewrite.py`) **változatlan** marad; a service-ek és az `llm_tasks` ezeket hívják.

---

### Task 1: Mode-enumok

**Files:**
- Create: `backend/modes.py`
- Test: `tests/test_modes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_modes.py
from backend.modes import (
    ClassifyMode, GenerationMode, VerifyMode, EscalationMode, OrchestratorMode,
)


def test_modes_are_str_backward_compatible():
    # str-alapú enum: a meglévő string-összehasonlítások változatlanul működnek
    assert ClassifyMode.LLM == "llm"
    assert ClassifyMode.RULE == "rule"
    assert GenerationMode.LLM == "llm"
    assert GenerationMode.TEMPLATE == "template"
    assert GenerationMode.INSUFFICIENT == "insufficient"
    assert VerifyMode.LLM == "llm"
    assert VerifyMode.HEURISTIC == "heuristic"
    assert EscalationMode.RULE == "rule"
    assert EscalationMode.RULE_LLM == "rule+llm"
    assert OrchestratorMode.LLM == "llm"
    assert OrchestratorMode.FALLBACK == "fallback"


def test_mode_json_serializes_as_plain_string():
    import json
    assert json.dumps({"m": GenerationMode.LLM}) == '{"m": "llm"}'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_modes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.modes'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/modes.py
from __future__ import annotations

from enum import Enum


class ClassifyMode(str, Enum):
    LLM = "llm"
    RULE = "rule"


class GenerationMode(str, Enum):
    LLM = "llm"
    TEMPLATE = "template"
    INSUFFICIENT = "insufficient"


class VerifyMode(str, Enum):
    LLM = "llm"
    HEURISTIC = "heuristic"


class EscalationMode(str, Enum):
    RULE = "rule"
    RULE_LLM = "rule+llm"


class OrchestratorMode(str, Enum):
    LLM = "llm"
    FALLBACK = "fallback"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_modes.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/modes.py tests/test_modes.py
git commit -m "Add str-based mode enums (roadmap #3)"
```

---

### Task 2: Egységes timeline-séma

**Files:**
- Create: `backend/timeline.py`
- Test: `tests/test_timeline.py`

A meglévő `agent/nodes.py::_timeline_entry` csak `{step, output}`-ot ad. Az új gyártó ennek **szuperhalmaza**: megtartja a `step` és `output` mezőt (frontend-kompatibilitás), és hozzáadja a diagnosztikai mezőket (`mode`, `status`, `counts`, `warnings`, `summary`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_timeline.py
from backend.timeline import timeline_entry


def test_timeline_entry_is_superset_of_legacy_shape():
    entry = timeline_entry(
        "classify",
        output={"category": "szamlazas"},
        mode="llm",
        status="ok",
        counts={"candidates": 2},
        summary="Számlázás, 89% konfidencia",
    )
    # Legacy mezők megmaradnak (a frontend ezeket olvassa)
    assert entry["step"] == "classify"
    assert entry["output"] == {"category": "szamlazas"}
    # Új diagnosztikai mezők
    assert entry["mode"] == "llm"
    assert entry["status"] == "ok"
    assert entry["counts"] == {"candidates": 2}
    assert entry["warnings"] == []
    assert entry["summary"] == "Számlázás, 89% konfidencia"


def test_timeline_entry_defaults():
    entry = timeline_entry("mask_input", output={"token_count": 3})
    assert entry["mode"] == "rule"
    assert entry["status"] == "ok"
    assert entry["counts"] == {}
    assert entry["warnings"] == []
    assert entry["summary"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timeline.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.timeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/timeline.py
from __future__ import annotations

from typing import Any


def timeline_entry(
    step: str,
    *,
    output: dict[str, Any] | None = None,
    mode: str = "rule",
    status: str = "ok",
    counts: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    summary: str = "",
) -> dict[str, Any]:
    """Egységes timeline-bejegyzés. A `step`+`output` a legacy alak (frontend ezt olvassa);
    a `mode/status/counts/warnings/summary` a diagnosztikai szuperhalmaz (roadmap #6)."""
    return {
        "step": step,
        "output": output or {},
        "mode": mode,
        "status": status,
        "counts": counts or {},
        "warnings": warnings or [],
        "summary": summary,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timeline.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/timeline.py tests/test_timeline.py
git commit -m "Add unified timeline entry schema (roadmap #6)"
```

---

### Task 3: Központi LLM-boundary (`llm_tasks.py`)

**Files:**
- Create: `backend/llm_tasks.py`
- Test: `tests/test_llm_tasks.py`

Egységes belépési felület az LLM-támogatott taszkokhoz. Minden függvény a meglévő `backend/` logikát hívja, és egységes `{mode, result, error}` alakot ad — így a Copilot subagentek (és a node-ok) egyformán kezelhetik a fallbacket.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_tasks.py
from backend import llm_tasks


def test_classify_task_offline_returns_rule_mode():
    # conftest offline-ra kényszerít → a wrap a 'rule' módot tükrözi
    out = llm_tasks.classify_message_task("Számlázási hibám van", history_summary_masked=None)
    assert out["error"] is None
    assert out["mode"] == "rule"
    assert out["result"]["category"] == "szamlazas"


def test_verify_task_wraps_result_and_mode():
    chunks = [{"chunk_id": "c1", "quote": "A felmondási idő 30 nap."}]
    out = llm_tasks.verify_grounding_task(
        draft_body_masked="A felmondási idő 30 nap. [S1]",
        chunks=chunks,
        mandatory_refs=[],
        citations=["c1"],
    )
    assert out["error"] is None
    assert out["mode"] in {"llm", "heuristic"}
    assert "ungrounded_count" in out["result"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_llm_tasks.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.llm_tasks'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/llm_tasks.py
from __future__ import annotations

import logging
from typing import Any

from backend.classify import classify_message
from backend.draft import synthesize_answer
from backend.escalation import decide_escalation, llm_escalation_suggestion, merge_escalation
from backend.query_rewrite import rewrite_query
from backend.verify import verify_draft

logger = logging.getLogger(__name__)


def _ok(mode: str, result: Any) -> dict[str, Any]:
    return {"mode": mode, "result": result, "error": None}


def _fail(error: str, fallback: Any, mode: str) -> dict[str, Any]:
    return {"mode": mode, "result": fallback, "error": error}


def classify_message_task(
    message_text_masked: str, history_summary_masked: str | None = None
) -> dict[str, Any]:
    try:
        result = classify_message(message_text_masked, history_summary_masked)
        return _ok(result.get("classify_mode", "rule"), result)
    except Exception as exc:  # a belső függvény már fallbackel, ez csak végső háló
        logger.exception("classify_message_task failed")
        return _fail(str(exc), {"category": "egyeb", "confidence": 0.0, "candidates": []}, "rule")


def rewrite_query_task(text: str, category: str) -> dict[str, Any]:
    try:
        query = rewrite_query(text, category)
        return _ok("llm" if query != text else "rule", query)
    except Exception as exc:
        logger.exception("rewrite_query_task failed")
        return _fail(str(exc), text, "rule")


def suggest_escalation_task(
    *,
    confidence: float,
    confidence_threshold: float,
    is_repeated: bool,
    missing_mandatory: list[str],
    sla_expired: bool,
    trigger_hits: list[str],
    text_masked: str,
    category: str,
    policy_coverage: bool,
) -> dict[str, Any]:
    try:
        rule = decide_escalation(
            confidence=confidence,
            confidence_threshold=confidence_threshold,
            is_repeated=is_repeated,
            missing_mandatory=missing_mandatory,
            sla_expired=sla_expired,
            trigger_hits=trigger_hits,
        )
        suggestion = llm_escalation_suggestion(
            text_masked=text_masked,
            category=category,
            confidence=confidence,
            policy_coverage=policy_coverage,
        )
        merged = merge_escalation(rule, suggestion)
        mode = "rule+llm" if suggestion.get("suggested") else "rule"
        return _ok(mode, merged)
    except Exception as exc:
        logger.exception("suggest_escalation_task failed")
        return _fail(str(exc), {"required": False, "reasons": []}, "rule")


def synthesize_answer_task(**kwargs: Any) -> dict[str, Any]:
    try:
        result = synthesize_answer(**kwargs)
        return _ok(result.get("generation_mode", "template"), result)
    except Exception as exc:
        logger.exception("synthesize_answer_task failed")
        return _fail(str(exc), {"body_masked": "", "generation_mode": "insufficient"}, "insufficient")


def verify_grounding_task(
    *,
    draft_body_masked: str,
    chunks: list[dict[str, Any]],
    mandatory_refs: list[str],
    citations: list[str] | None = None,
) -> dict[str, Any]:
    try:
        result = verify_draft(
            draft_body_masked=draft_body_masked,
            chunks=chunks,
            mandatory_refs=mandatory_refs,
            citations=citations,
        )
        return _ok(result.get("verify_mode", "heuristic"), result)
    except Exception as exc:
        logger.exception("verify_grounding_task failed")
        return _fail(str(exc), {"ungrounded_count": 0, "claims": []}, "heuristic")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_llm_tasks.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/llm_tasks.py tests/test_llm_tasks.py
git commit -m "Add central LLM task boundary with uniform mode/result/error (roadmap #2)"
```

---

### Task 4: Eset-szintű service-réteg

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/classification_service.py`
- Create: `backend/services/rag_service.py`
- Create: `backend/services/approval_service.py`
- Test: `tests/test_services.py`

A service-ek eset/forduló-orientált műveletekbe fogják az alacsonyabb szintű függvényeket. Ezeket hívják majd a Copilot subagentek ÉS (későbbi opcionális lépésben) a node-ok.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_services.py
from backend.services import classification_service, rag_service, approval_service


def test_classification_service_returns_category_and_mode():
    out = classification_service.classify("Nincs internetem napok óta", history_summary_masked=None)
    assert out["category"] == "hibabejelentes_szolgaltataskieses"
    assert out["mode"] in {"rule", "llm"}


def test_rag_service_retrieve_for_case_packages_chunks_and_policy_map():
    out = rag_service.retrieve_for_case(
        text_masked="Mennyi a felmondási idő?",
        category="szerzodesfelmondas_modositas",
        service_provider=None,
    )
    assert "chunks" in out
    assert "policy_map" in out
    assert "result_count" in out
    assert "policy_items" in out["policy_map"]


def test_approval_service_prepare_preview_strips_markers():
    preview = approval_service.prepare_preview(
        case_id="CHAT-test",
        subject="Tárgy [S1]",
        body_masked="A felmondási idő 30 nap. [S1]",
    )
    assert "[S1]" not in preview["subject_unmasked"]
    assert "[S1]" not in preview["body_unmasked"]
    assert "ready_for_approval" in preview
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_services.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/services/__init__.py
```

```python
# backend/services/classification_service.py
from __future__ import annotations

from typing import Any

from backend import llm_tasks


def classify(message_text_masked: str, history_summary_masked: str | None = None) -> dict[str, Any]:
    """Egységes besorolási művelet: kategória + mód egy helyen."""
    task = llm_tasks.classify_message_task(message_text_masked, history_summary_masked)
    result = task["result"]
    return {
        "category": result.get("category", "egyeb"),
        "subtype": result.get("subtype"),
        "confidence": result.get("confidence", 0.0),
        "candidates": result.get("candidates", []),
        "is_repeated": result.get("is_repeated", False),
        "mode": task["mode"],
    }
```

```python
# backend/services/rag_service.py
from __future__ import annotations

from typing import Any

from backend import llm_tasks
from backend.policy_map import build_policy_map
from backend.retrieval import retrieve


def retrieve_for_case(
    text_masked: str,
    category: str,
    service_provider: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Egy menetben: keresőkérdés-újraírás → retrieval → policy-map csomagolás."""
    rewrite = llm_tasks.rewrite_query_task(text_masked, category)
    search_query = rewrite["result"][:400]
    retrieval = retrieve(
        query=search_query,
        service_provider=service_provider,
        limit=limit,
        category=category,
    )
    chunks = retrieval.get("chunks", [])
    policy_map = build_policy_map(category=category, chunks=chunks)
    return {
        "search_query": search_query,
        "chunks": chunks,
        "result_count": retrieval.get("result_count", 0),
        "unresolved_refs": retrieval.get("unresolved_refs", []),
        "policy_map": policy_map,
        "rewrite_mode": rewrite["mode"],
    }
```

```python
# backend/services/approval_service.py
from __future__ import annotations

from typing import Any

from backend.draft import strip_source_markers
from backend.masking import unmask_text


def prepare_preview(
    case_id: str,
    subject: str,
    body_masked: str,
    *,
    verify_warning: bool = False,
    escalation_required: bool = False,
    generation_mode: str = "llm",
) -> dict[str, Any]:
    """Jóváhagyási előnézet: unmask + forrásjelölő-eltávolítás csak az ügyfél-felé menő szövegen."""
    ready_for_approval = (
        not verify_warning and not escalation_required and generation_mode != "insufficient"
    )
    return {
        "subject_unmasked": strip_source_markers(unmask_text(case_id, subject)),
        "body_unmasked": strip_source_markers(unmask_text(case_id, body_masked)),
        "ready_for_approval": ready_for_approval,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_services.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/ tests/test_services.py
git commit -m "Add case-level service layer over business logic (roadmap #1)"
```

---

### Task 5: Golden-case regressziós háló

**Files:**
- Test: `tests/test_golden_cases.py`

Kicsi, gyorsan futó end-to-end háló a kritikus útvonalakra (roadmap #10). A meglévő `agent.runner.run_agent`-et hívja offline (conftest) — ez védi a refaktort és a későbbi orchestratort egyaránt.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_golden_cases.py
import pytest

from agent.runner import run_agent


GOLDEN = [
    ("szamla", "Túl magas a havi számlám, kérem nézzék meg.", "szamlazas"),
    ("hiba", "Napok óta nincs internetem, állandóan szakad.", "hibabejelentes_szolgaltataskieses"),
    ("felmondas", "Fel szeretném mondani a szerződésemet, mennyi a felmondási idő?", "szerzodesfelmondas_modositas"),
]


@pytest.mark.parametrize("name,text,expected_category", GOLDEN)
def test_golden_case_category_and_timeline(name, text, expected_category):
    out = run_agent(case_id=f"GOLD-{name}", channel="email", input_text=text)
    assert out["classification"]["category"] == expected_category
    # A timeline minden várt lépést tartalmaz, és nincs PII-szivárgás a nyers szövegből
    steps = [t["step"] for t in out["timeline"]]
    assert "classify" in steps and "draft" in steps and "verify" in steps


def test_golden_insufficient_path_sets_insufficient_mode():
    # Értelmetlen, fedezet nélküli kérés → insufficient generation_mode
    out = run_agent(case_id="GOLD-insuff", channel="email", input_text="zzz qqq xyz")
    assert out["draft"]["generation_mode"] in {"insufficient", "template"}
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_golden_cases.py -q`
Expected: Ha a kategorizálás már most helyes, PASS; ha valamelyik golden eltér, a teszt megmutatja a tényleges kategóriát — ekkor igazítsd a `expected_category`-t a valós, helyes viselkedéshez (ez rögzíti a baseline-t), NE a kódot.

- [ ] **Step 3: Rögzítsd a baseline-t**

Ha egy eset a kód helyes viselkedése miatt más kategóriát ad, frissítsd a `GOLDEN` várt értékét a ténylegesre. A cél a *jelenlegi helyes* viselkedés befagyasztása, nem a kód módosítása.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_golden_cases.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_golden_cases.py
git commit -m "Add golden-case regression net for agent pipeline (roadmap #10)"
```

---

### Task 6: Node-ok átkötése a service-ekre és az egységes timeline-ra

**Files:**
- Modify: `agent/nodes.py` (`classify_node`, `retrieve_node`+`policy_map_node`, `_append_timeline` használat)
- Test: `tests/test_golden_cases.py` (regresszióként újrafuttatva)

Cél: bizonyítani, hogy a service-réteg behelyettesíthető a node-okba a viselkedés változása nélkül. Egy node-ot kötünk át mintaként (`classify_node`), a golden teszt védőhálóként fut.

- [ ] **Step 1: Run the regression net (zöld kiindulás)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_golden_cases.py -q`
Expected: PASS (a Task 5 utáni állapot)

- [ ] **Step 2: Kösd át a `classify_node`-ot a service-re**

`agent/nodes.py` — a `classify_node` jelenlegi törzsét cseréld erre (a `nem_panasz`/`hatokoron_kivuli` felülírás marad):

```python
def classify_node(state: AgentState) -> AgentState:
    from backend.services import classification_service
    svc = classification_service.classify(
        message_text_masked=_active_text(state),
        history_summary_masked=state.get("history_summary_masked"),
    )
    result = {
        "category": svc["category"],
        "subtype": svc["subtype"],
        "confidence": svc["confidence"],
        "candidates": svc["candidates"],
        "is_repeated": svc["is_repeated"],
        "classify_mode": svc["mode"],
    }
    if state.get("lang_type", {}).get("tipus") == "nem_panasz":
        result["category"] = "egyeb"
        result["subtype"] = "nem_panasz"
    if state.get("lang_type", {}).get("tipus") == "hatokoron_kivuli":
        result["category"] = "egyeb"
        result["subtype"] = "hatokoron_kivuli"
    return {
        "classification": result,
        "timeline": _append_timeline(state, "classify", result),
    }
```

- [ ] **Step 3: Run the regression net to verify no behavior change**

Run: `.venv/Scripts/python.exe -m pytest tests/test_golden_cases.py tests/test_services.py -q`
Expected: PASS (változatlan viselkedés)

- [ ] **Step 4: Teljes backend teszt**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (a `test_settings_have_local_qdrant_defaults` ismert, független bukása megengedett — lásd CLAUDE.md)

- [ ] **Step 5: Commit**

```bash
git add agent/nodes.py
git commit -m "Route classify_node through classification_service (roadmap #1)"
```

---

## Self-Review checklist (a terv írója futtatta)

- **Spec lefedettség (§5 A):** #10/#8 → Task 5; #1 → Task 4+6; #2 → Task 3; #3 → Task 1; #6 → Task 2. Lefedve.
- **Placeholder-scan:** nincs TBD/"handle errors" — minden lépésben valós kód és parancs.
- **Típus-konzisztencia:** `classify_message_task`/`classify` mezőnevek (`category`, `mode`) végig egyeznek; a `timeline_entry` mezői (`step/output/mode/status/counts/warnings/summary`) konzisztensek.
- **Megjegyzés:** a contract-tesztek (roadmap #8) bővebb endpoint-lefedése a Copilot-végpont megírásakor (Plan 2, Task 6) természetesebb; itt a golden-háló adja a regressziós védelmet.
