# Copilot orchestrator (nem-determinisztikus agent) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Külön `agent/copilot/` ágon egy nem-determinisztikus, LLM tool-calling orchestrator, amely körönként eldönti, melyik subagentet hívja, visszakérdez, vagy végleges választ ad — a lineáris inbox pipeline érintetlenül hagyásával.

**Architecture:** Az orchestrator LLM a `backend/llm.py::chat_json` JSON-object idiómán fut; a subagentek a Plan 1 service-rétegét (`rag_service`, `classification_service`, `approval_service`, `llm_tasks`) csomagolják vékony adapterként. Kötelező maszkoló kapu belépéskor és forrásjelölő-eltávolítás kilépéskor; minden lépés egységes timeline-bejegyzést és `*_mode`-ot ad. Determinisztikus fallback, ha nincs LLM.

**Tech Stack:** Python 3 (FastAPI), pytest hermetikus offline; React + TS + Vite frontend. Windows/PowerShell: `;` lánc, `python -m pytest`.

**Függőség:** Ez a terv a **Copilot előfeltétel-refactor** (`2026-06-09-copilot-prerequisite-refactor.md`) befejezett állapotára épül — kell a `backend/services/`, `backend/llm_tasks.py`, `backend/modes.py`, `backend/timeline.py`.

---

## Fájlszerkezet

- Create: `agent/copilot/__init__.py`
- Create: `agent/copilot/session.py` — több fordulós session-állapot (maszkolt üzenet, gyűjtött adatok, timeline).
- Create: `agent/copilot/tools_spec.py` — a tool-menü (név, leírás, paraméterek) + prompt-formázó.
- Create: `agent/copilot/subagents.py` — a 6 subagent mint vékony adapter a service-ek fölött.
- Create: `agent/copilot/orchestrator.py` — az LLM tool-calling ciklus + determinisztikus fallback.
- Create: `agent/copilot/runner.py` — `run_copilot_turn(...)`: maszk kapu → ciklus → kilépő kapu.
- Create: `backend/api/copilot.py` — `POST /copilot/chat` router.
- Modify: `backend/api/contracts.py` — `CopilotChatRequest` / `CopilotChatResponse`.
- Modify: `backend/main.py` — a copilot router regisztrálása.
- Modify: `frontend/src/lib/types.ts` — Copilot-válasz típusok.
- Modify: `frontend/src/lib/api.ts` — `copilotChat` metódus.
- Modify: `frontend/src/lib/agentSteps.ts` — `STEP_META` az új subagent-lépésekhez.
- Modify: `frontend/src/screens/Copilot.tsx` — átállás `agentRun`-ról `copilotChat`-re.
- Tests: `tests/test_copilot_subagents.py`, `tests/test_copilot_orchestrator.py`, `tests/test_copilot_runner.py`, `tests/test_copilot_api.py`.

---

### Task 1: Session-állapot

**Files:**
- Create: `agent/copilot/__init__.py` (üres)
- Create: `agent/copilot/session.py`
- Test: `tests/test_copilot_subagents.py` (a session-t is itt teszteljük először)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_copilot_subagents.py
from agent.copilot.session import CopilotSession


def test_session_holds_masked_text_and_accumulates_timeline():
    s = CopilotSession(session_id="CHAT-1", message_masked="Számlázási hibám van [NÉV_1]")
    assert s.session_id == "CHAT-1"
    assert s.timeline == []
    s.record(step="classify", output={"category": "szamlazas"}, mode="rule", summary="számlázás")
    assert len(s.timeline) == 1
    assert s.timeline[0]["step"] == "classify"
    assert s.timeline[0]["summary"] == "számlázás"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_subagents.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.copilot'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/copilot/__init__.py
```

```python
# agent/copilot/session.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.timeline import timeline_entry


@dataclass
class CopilotSession:
    """Egy Copilot beszélgetés-forduló állapota. CSAK maszkolt szövegen dolgozik."""

    session_id: str
    message_masked: str
    history: list[dict[str, str]] = field(default_factory=list)
    classification: dict[str, Any] | None = None
    retrieval: dict[str, Any] | None = None
    customer: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None
    draft: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        *,
        step: str,
        output: dict[str, Any] | None = None,
        mode: str = "rule",
        status: str = "ok",
        counts: dict[str, Any] | None = None,
        summary: str = "",
    ) -> None:
        self.timeline.append(
            timeline_entry(
                step, output=output, mode=mode, status=status, counts=counts, summary=summary
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_subagents.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot/__init__.py agent/copilot/session.py tests/test_copilot_subagents.py
git commit -m "Add CopilotSession state for the orchestrator turn"
```

---

### Task 2: Subagentek (adapterek a service-ek fölött)

**Files:**
- Create: `agent/copilot/subagents.py`
- Test: `tests/test_copilot_subagents.py` (bővítés)

Minden subagent: maszkolt szövegen dolgozik, a session-be ír (cache + timeline), és visszaad egy rövid, az orchestratornak szóló `observation` szótárt.

- [ ] **Step 1: Write the failing tests (append)**

```python
# tests/test_copilot_subagents.py  (add to existing file)
from agent.copilot import subagents
from agent.copilot.session import CopilotSession


def test_knowledge_search_populates_retrieval_and_timeline():
    s = CopilotSession(session_id="CHAT-2", message_masked="Mennyi a felmondási idő?")
    obs = subagents.knowledge_search(s, category="szerzodesfelmondas_modositas")
    assert s.retrieval is not None
    assert "result_count" in obs
    assert any(t["step"] == "knowledge_search" for t in s.timeline)


def test_classify_subagent_sets_classification():
    s = CopilotSession(session_id="CHAT-3", message_masked="Nincs internetem napok óta")
    obs = subagents.classify(s)
    assert s.classification["category"] == "hibabejelentes_szolgaltataskieses"
    assert obs["category"] == "hibabejelentes_szolgaltataskieses"
    assert any(t["step"] == "classify" for t in s.timeline)


def test_draft_reply_requires_retrieval_first():
    s = CopilotSession(session_id="CHAT-4", message_masked="Mennyi a felmondási idő?")
    subagents.knowledge_search(s, category="szerzodesfelmondas_modositas")
    obs = subagents.draft_reply(s, category="szerzodesfelmondas_modositas")
    assert s.draft is not None
    assert "generation_mode" in obs
    assert any(t["step"] == "draft_reply" for t in s.timeline)


def test_subagents_registry_contains_all_tools():
    assert set(subagents.SUBAGENTS) == {
        "classify", "knowledge_search", "customer_context",
        "escalation_advice", "draft_reply", "verify_grounding",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_subagents.py -q`
Expected: FAIL — `AttributeError: module 'agent.copilot.subagents' has no attribute ...`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/copilot/subagents.py
from __future__ import annotations

from typing import Any

from agent.copilot.session import CopilotSession
from backend import llm_tasks
from backend.history import get_history
from backend.services import classification_service, rag_service
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory


def classify(session: CopilotSession, **_: Any) -> dict[str, Any]:
    svc = classification_service.classify(session.message_masked)
    session.classification = svc
    session.record(
        step="classify",
        output={"category": svc["category"], "confidence": svc["confidence"]},
        mode=svc["mode"],
        summary=f'{svc["category"]} ({round(svc["confidence"] * 100)}%)',
    )
    return {"category": svc["category"], "confidence": svc["confidence"], "subtype": svc["subtype"]}


def knowledge_search(session: CopilotSession, *, category: str | None = None, **_: Any) -> dict[str, Any]:
    cat = category or (session.classification or {}).get("category") or "egyeb"
    result = rag_service.retrieve_for_case(
        text_masked=session.message_masked, category=cat, service_provider=None
    )
    session.retrieval = result
    session.record(
        step="knowledge_search",
        output={"search_query": result["search_query"][:120], "result_count": result["result_count"]},
        mode=result["rewrite_mode"],
        counts={"results": result["result_count"], "policy_items": len(result["policy_map"].get("policy_items", []))},
        summary=f'{result["result_count"]} találat',
    )
    return {
        "result_count": result["result_count"],
        "policy_item_count": len(result["policy_map"].get("policy_items", [])),
        "sources": [
            {"ref": f"S{i+1}", "idezet": it.get("idezet", "")[:160]}
            for i, it in enumerate(result["policy_map"].get("policy_items", []))
        ],
    }


def customer_context(session: CopilotSession, *, sender_email: str | None = None, **_: Any) -> dict[str, Any]:
    if not sender_email:
        session.record(step="customer_context", output={"history_loaded": False}, summary="nincs feladó")
        return {"history_loaded": False, "is_repeated": False, "customer_count": 0}
    history = get_history(sender_email)
    candidates = MockCustomerDirectory().lookup_by_email(sender_email)
    session.customer = {"history": history, "candidates": candidates}
    session.record(
        step="customer_context",
        output={"history_loaded": True, "customer_count": len(candidates)},
        counts={"customers": len(candidates)},
        summary=f'{len(candidates)} ügyfél-jelölt',
    )
    return {
        "history_loaded": True,
        "is_repeated": bool(history.get("is_repeated")),
        "customer_count": len(candidates),
    }


def escalation_advice(session: CopilotSession, **_: Any) -> dict[str, Any]:
    classification = session.classification or {}
    policy_map = (session.retrieval or {}).get("policy_map", {})
    task = llm_tasks.suggest_escalation_task(
        confidence=float(classification.get("confidence", 0.0)),
        confidence_threshold=float(settings.confidence_threshold),
        is_repeated=bool(classification.get("is_repeated")),
        missing_mandatory=list(policy_map.get("missing_mandatory", [])),
        sla_expired=False,
        trigger_hits=[],
        text_masked=session.message_masked,
        category=str(classification.get("category", "egyeb")),
        policy_coverage=bool(policy_map.get("policy_items")),
    )
    session.escalation = task["result"]
    session.record(
        step="escalation_advice",
        output={"required": task["result"].get("required"), "reasons": task["result"].get("reasons", [])},
        mode=task["mode"],
        summary="eszkaláció szükséges" if task["result"].get("required") else "nem kell eszkaláció",
    )
    return {"required": bool(task["result"].get("required")), "reasons": task["result"].get("reasons", [])}


def draft_reply(session: CopilotSession, *, category: str | None = None, **_: Any) -> dict[str, Any]:
    cat = category or (session.classification or {}).get("category") or "egyeb"
    policy_map = (session.retrieval or {}).get("policy_map", {})
    task = llm_tasks.synthesize_answer_task(
        case_id=session.session_id,
        category=cat,
        channel="chat",
        output_mode="hitl",
        policy_map=policy_map,
        actions=[],
        input_text_masked=session.message_masked,
    )
    session.draft = task["result"]
    session.record(
        step="draft_reply",
        output={
            "format": task["result"].get("format"),
            "generation_mode": task["result"].get("generation_mode"),
            "source_count": len(task["result"].get("sources", [])),
        },
        mode=task["mode"],
        summary=f'draft ({task["result"].get("generation_mode")})',
    )
    return {
        "generation_mode": task["result"].get("generation_mode"),
        "body_masked": task["result"].get("body_masked", ""),
        "source_count": len(task["result"].get("sources", [])),
    }


def verify_grounding(session: CopilotSession, **_: Any) -> dict[str, Any]:
    draft = session.draft or {}
    chunks = (session.retrieval or {}).get("chunks", [])
    task = llm_tasks.verify_grounding_task(
        draft_body_masked=draft.get("body_masked", ""),
        chunks=chunks,
        mandatory_refs=[],
        citations=[str(c) for c in draft.get("citations", []) if c],
    )
    session.record(
        step="verify_grounding",
        output={"ungrounded_count": task["result"].get("ungrounded_count", 0)},
        mode=task["mode"],
        summary=f'{task["result"].get("ungrounded_count", 0)} nem megalapozott',
    )
    return {"ungrounded_count": task["result"].get("ungrounded_count", 0)}


SUBAGENTS = {
    "classify": classify,
    "knowledge_search": knowledge_search,
    "customer_context": customer_context,
    "escalation_advice": escalation_advice,
    "draft_reply": draft_reply,
    "verify_grounding": verify_grounding,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_subagents.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot/subagents.py tests/test_copilot_subagents.py
git commit -m "Add Copilot subagents as thin adapters over service layer"
```

---

### Task 3: Tool-menü specifikáció

**Files:**
- Create: `agent/copilot/tools_spec.py`
- Test: `tests/test_copilot_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_copilot_orchestrator.py
from agent.copilot import tools_spec
from agent.copilot.subagents import SUBAGENTS


def test_tools_spec_matches_subagent_registry():
    spec_names = {t["name"] for t in tools_spec.TOOLS}
    assert spec_names == set(SUBAGENTS)


def test_tools_prompt_lists_every_tool():
    prompt = tools_spec.tools_prompt()
    for t in tools_spec.TOOLS:
        assert t["name"] in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_orchestrator.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.copilot.tools_spec'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/copilot/tools_spec.py
from __future__ import annotations

TOOLS = [
    {"name": "classify", "description": "Az üzenet panaszkategóriájának és konfidenciájának megállapítása.", "args": {}},
    {"name": "knowledge_search", "description": "ÁSZF-források keresése a kérdéshez (forrásjelölőkkel).", "args": {"category": "opcionális kategória"}},
    {"name": "customer_context", "description": "Korábbi ügyek és ügyfél-rekord lekérése a feladó alapján.", "args": {"sender_email": "feladó e-mail, ha van"}},
    {"name": "escalation_advice", "description": "Javasolt-e supervisor-eszkaláció, és miért.", "args": {}},
    {"name": "draft_reply", "description": "Ügyfél-felé menő válasz-draft a talált forrásokból. Előbb knowledge_search kell.", "args": {"category": "opcionális kategória"}},
    {"name": "verify_grounding", "description": "A draft állításai a forrásokon alapulnak-e. Előbb draft_reply kell.", "args": {}},
]


def tools_prompt() -> str:
    lines = ["Elérhető eszközök (tool-ok):"]
    for t in TOOLS:
        args = ", ".join(t["args"]) if t["args"] else "(nincs paraméter)"
        lines.append(f'- {t["name"]}: {t["description"]} Paraméterek: {args}')
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_orchestrator.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot/tools_spec.py tests/test_copilot_orchestrator.py
git commit -m "Add Copilot tool-menu spec"
```

---

### Task 4: Orchestrator-ciklus (LLM tool-calling + fallback)

**Files:**
- Create: `agent/copilot/orchestrator.py`
- Test: `tests/test_copilot_orchestrator.py` (bővítés)

- [ ] **Step 1: Write the failing tests (append)**

```python
# tests/test_copilot_orchestrator.py  (add to existing file)
from agent.copilot import orchestrator
from agent.copilot.session import CopilotSession
from config.settings import settings


def test_orchestrator_fallback_path_when_no_llm(monkeypatch):
    # conftest offline → fallback út: legalább knowledge_search + draft, és van válasz
    s = CopilotSession(session_id="CHAT-O1", message_masked="Mennyi a felmondási idő?")
    result = orchestrator.run(s)
    assert result["orchestrator_mode"] == "fallback"
    assert isinstance(result["reply_masked"], str) and result["reply_masked"]
    steps = [t["step"] for t in result["timeline"]]
    assert "knowledge_search" in steps


def test_orchestrator_llm_loop_calls_chosen_tools(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr("backend.llm.llm_available", lambda: True)
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: True)

    # Az LLM először knowledge_search-öt kér, majd válaszol
    scripted = [
        {"action": "call_tool", "tool": "knowledge_search", "args": {"category": "szerzodesfelmondas_modositas"}},
        {"action": "respond", "reply": "A felmondási idő a forrás szerint 30 nap. [S1]"},
    ]
    calls = {"i": 0}

    def fake_decide(system, user):
        out = scripted[calls["i"]]
        calls["i"] += 1
        return out

    monkeypatch.setattr("agent.copilot.orchestrator.chat_json", fake_decide)

    s = CopilotSession(session_id="CHAT-O2", message_masked="Mennyi a felmondási idő?")
    result = orchestrator.run(s)
    assert result["orchestrator_mode"] == "llm"
    assert "30 nap" in result["reply_masked"]
    assert any(t["step"] == "knowledge_search" for t in result["timeline"])


def test_orchestrator_respects_iteration_cap(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: True)
    # Mindig tool-t kér → a ciklus-korlát megállítja
    monkeypatch.setattr(
        "agent.copilot.orchestrator.chat_json",
        lambda system, user: {"action": "call_tool", "tool": "classify", "args": {}},
    )
    s = CopilotSession(session_id="CHAT-O3", message_masked="bla")
    result = orchestrator.run(s)
    tool_steps = [t for t in result["timeline"] if t["step"] in ("classify",)]
    assert len(tool_steps) <= orchestrator.MAX_ITERATIONS
    assert result["reply_masked"]  # a korlát elérésekor is van valamilyen válasz
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_orchestrator.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.copilot.orchestrator'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/copilot/orchestrator.py
from __future__ import annotations

import json
import logging
from typing import Any

from agent.copilot import tools_spec
from agent.copilot.session import CopilotSession
from agent.copilot.subagents import SUBAGENTS
from backend.llm import chat_json, llm_available
from backend.modes import OrchestratorMode

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8

ORCHESTRATOR_SYSTEM = (
    "Belső ügyintézői copilot ORCHESTRÁTORA vagy. Egy ügyintéző kérdésére dolgozol.\n"
    "Körönként EGY döntést hozol JSON-ban, az alábbi sémák egyikében:\n"
    '{"action":"call_tool","tool":"<név>","args":{...}}  — egy eszköz meghívása,\n'
    '{"action":"respond","reply":"<az ügyintézőnek szóló válasz>"}  — végleges válasz,\n'
    '{"action":"ask_user","question":"<pontosító kérdés>"}  — ha kevés az információ.\n'
    "Szabályok: csak a megadott eszközöket hívd; ne találj ki tényt; a forrásjelölőket ([S1]) tartsd meg; "
    "a maszkolt PII-t (pl. [NÉV_1]) hagyd érintetlenül.\n"
    + tools_spec.tools_prompt()
)


def _observation_block(observations: list[dict[str, Any]]) -> str:
    if not observations:
        return "(még nincs eszköz-eredmény)"
    return "\n".join(
        f'- {o["tool"]} → {json.dumps(o["result"], ensure_ascii=False)[:600]}' for o in observations
    )


def _decide(session: CopilotSession, observations: list[dict[str, Any]]) -> dict[str, Any]:
    user = (
        f'Ügyintéző kérdése (maszkolt):\n"""\n{session.message_masked}\n"""\n'
        f"Eddigi eszköz-eredmények:\n{_observation_block(observations)}\n"
        "Mi a következő döntésed?"
    )
    return chat_json(ORCHESTRATOR_SYSTEM, user)


def _fallback_reply(session: CopilotSession) -> str:
    if session.draft and session.draft.get("body_masked"):
        return session.draft["body_masked"]
    return (
        "Nincs elegendő ÁSZF-fedezet automatikus válaszhoz. "
        "Emberi ellenőrzés / eszkaláció javasolt."
    )


def _run_fallback(session: CopilotSession) -> dict[str, Any]:
    """Determinisztikus út LLM nélkül: osztályozás → keresés → (eszkaláció vagy draft)."""
    SUBAGENTS["classify"](session)
    SUBAGENTS["knowledge_search"](session)
    esc = SUBAGENTS["escalation_advice"](session)
    if not esc["required"]:
        SUBAGENTS["draft_reply"](session)
    reply = _fallback_reply(session)
    return _finalize(session, reply, OrchestratorMode.FALLBACK)


def _finalize(session: CopilotSession, reply_masked: str, mode: str) -> dict[str, Any]:
    sources = (session.retrieval or {}).get("policy_map", {}).get("policy_items", [])
    return {
        "reply_masked": reply_masked,
        "sources": sources,
        "draft": session.draft,
        "escalation": session.escalation,
        "timeline": session.timeline,
        "orchestrator_mode": mode,
    }


def run(session: CopilotSession) -> dict[str, Any]:
    if not llm_available():
        return _run_fallback(session)

    observations: list[dict[str, Any]] = []
    for _ in range(MAX_ITERATIONS):
        try:
            decision = _decide(session, observations)
        except Exception:
            logger.exception("orchestrator decide failed; switching to fallback")
            return _run_fallback(session)

        action = decision.get("action")
        if action == "respond":
            return _finalize(session, str(decision.get("reply", "")).strip(), OrchestratorMode.LLM)
        if action == "ask_user":
            return _finalize(session, str(decision.get("question", "")).strip(), OrchestratorMode.LLM)
        if action == "call_tool":
            tool = decision.get("tool")
            subagent = SUBAGENTS.get(tool)
            if not subagent:
                observations.append({"tool": tool, "result": {"error": "ismeretlen eszköz"}})
                continue
            args = decision.get("args") or {}
            try:
                result = subagent(session, **args)
            except Exception as exc:
                logger.exception("subagent %s failed", tool)
                result = {"error": str(exc)}
            observations.append({"tool": tool, "result": result})
            continue
        # ismeretlen action → leállás
        break

    # ciklus-korlát vagy ismeretlen action: a legjobb elérhető válasz
    session.record(step="iteration_cap", output={"iterations": MAX_ITERATIONS}, status="warning",
                   summary="elértük a ciklus-korlátot")
    return _finalize(session, _fallback_reply(session), OrchestratorMode.LLM)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_orchestrator.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot/orchestrator.py tests/test_copilot_orchestrator.py
git commit -m "Add Copilot orchestrator loop with LLM tool-calling and deterministic fallback"
```

---

### Task 5: Runner — maszkoló és kilépő kapuk

**Files:**
- Create: `agent/copilot/runner.py`
- Test: `tests/test_copilot_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_copilot_runner.py
from agent.copilot.runner import run_copilot_turn


def test_runner_masks_input_and_never_leaks_pii_to_timeline():
    raw = "Kovács János vagyok, mennyi a felmondási idő?"
    out = run_copilot_turn(session_id="CHAT-R1", message=raw, history=[])
    # A nyers név nem szerepelhet a timeline-ban (csak maszkolt token)
    serialized = str(out["timeline"])
    assert "Kovács János" not in serialized
    assert "reply" in out
    assert "orchestrator_mode" in out


def test_runner_strips_source_markers_from_customer_facing_reply():
    out = run_copilot_turn(
        session_id="CHAT-R2",
        message="Kérek egy ügyfélnek küldhető választ a felmondási időről.",
        history=[],
        customer_facing=True,
    )
    assert "[S" not in out["reply"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_runner.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.copilot.runner'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/copilot/runner.py
from __future__ import annotations

from typing import Any

from agent.copilot import orchestrator
from agent.copilot.session import CopilotSession
from backend.draft import strip_source_markers
from backend.masking import mask_text, unmask_text


def run_copilot_turn(
    session_id: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    customer_facing: bool = False,
) -> dict[str, Any]:
    """Egy Copilot-forduló: maszkoló kapu → orchestrator-ciklus → kilépő kapu."""
    # 1) Maszkoló kapu — csak maszkolt szöveg megy tovább
    masked = mask_text(session_id, message)
    session = CopilotSession(
        session_id=session_id,
        message_masked=masked["masked_text"],
        history=history or [],
    )

    # 2) Orchestrator-ciklus (maszkolt szövegen)
    result = orchestrator.run(session)

    # 3) Kilépő kapu — unmask az ügyintézőnek; ügyfél-felé menő szövegnél jelölő-eltávolítás
    reply_unmasked = unmask_text(session_id, result["reply_masked"])
    reply = strip_source_markers(reply_unmasked) if customer_facing else reply_unmasked

    return {
        "reply": reply,
        "sources": result["sources"],
        "draft": result["draft"],
        "escalation": result["escalation"],
        "timeline": result["timeline"],
        "orchestrator_mode": result["orchestrator_mode"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_runner.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/copilot/runner.py tests/test_copilot_runner.py
git commit -m "Add Copilot runner with mandatory mask/unmask gates"
```

---

### Task 6: Backend végpont (`POST /copilot/chat`)

**Files:**
- Modify: `backend/api/contracts.py` (új modellek a fájl végére)
- Create: `backend/api/copilot.py`
- Modify: `backend/main.py` (router regisztráció)
- Test: `tests/test_copilot_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_copilot_api.py
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_copilot_chat_endpoint_returns_reply_and_timeline():
    resp = client.post(
        "/copilot/chat",
        json={"session_id": "CHAT-API1", "message": "Mennyi a felmondási idő?", "history": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "timeline" in data
    assert "orchestrator_mode" in data


def test_copilot_chat_requires_message():
    resp = client.post("/copilot/chat", json={"session_id": "CHAT-API2", "message": "", "history": []})
    assert resp.status_code == 200
    assert resp.json().get("error")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_api.py -q`
Expected: FAIL — 404 (a `/copilot/chat` még nem létezik)

- [ ] **Step 3a: Add contracts**

`backend/api/contracts.py` végére:

```python
class CopilotChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    customer_facing: bool = False


class CopilotChatResponse(FlexibleResponse):
    reply: str | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    orchestrator_mode: str | None = None
    error: str | None = None
```

- [ ] **Step 3b: Create the router**

```python
# backend/api/copilot.py
from __future__ import annotations

from fastapi import APIRouter

from agent.copilot.runner import run_copilot_turn
from backend.metadata import response_meta

from .contracts import CopilotChatRequest, CopilotChatResponse

router = APIRouter()


@router.post("/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(payload: CopilotChatRequest) -> dict:
    if not payload.message.strip():
        return {**response_meta(), "error": "message kötelező"}
    result = run_copilot_turn(
        session_id=payload.session_id,
        message=payload.message,
        history=payload.history,
        customer_facing=payload.customer_facing,
    )
    return {**response_meta(), **result}
```

- [ ] **Step 3c: Register the router**

`backend/main.py` — a meglévő router-import blokk mellé:

```python
from backend.api.copilot import router as copilot_router
```

és a `app.include_router(agent_router)` után:

```python
app.include_router(copilot_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copilot_api.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/api/copilot.py backend/api/contracts.py backend/main.py tests/test_copilot_api.py
git commit -m "Add POST /copilot/chat endpoint"
```

---

### Task 7: Frontend átállás a Copilot végpontra

**Files:**
- Modify: `frontend/src/lib/types.ts` (új típus a fájl végére)
- Modify: `frontend/src/lib/api.ts` (új metódus)
- Modify: `frontend/src/lib/agentSteps.ts` (`STEP_META` bővítés)
- Modify: `frontend/src/screens/Copilot.tsx` (`agentRun` → `copilotChat`)

- [ ] **Step 1: Add the type**

`frontend/src/lib/types.ts` végére:

```typescript
export interface CopilotChatResponse {
  reply: string;
  sources?: SourceRef[];
  draft?: { generation_mode?: GenerationMode } | null;
  timeline: { step: string; output: Record<string, unknown>; summary?: string }[];
  orchestrator_mode: "llm" | "fallback";
}
```

- [ ] **Step 2: Add the api method**

`frontend/src/lib/api.ts` — az `agentRun` mellé:

```typescript
  copilotChat: (body: { session_id: string; message: string; history: { role: string; content: string }[]; customer_facing?: boolean }) =>
    req<import("./types").CopilotChatResponse>("POST", "/copilot/chat", body),
```

- [ ] **Step 3: Extend STEP_META for the new subagent steps**

`frontend/src/lib/agentSteps.ts` — a `STEP_META` objektumba (a `prepare_unmask` után, a záró `}` elé) vedd fel:

```typescript
  knowledge_search: {
    label: "ÁSZF-források keresése",
    explain: "Megkeresi a kérdéshez kapcsolódó ÁSZF-szakaszokat és forrásjelölőkkel visszaadja.",
    fields: ["search_query", "result_count"],
  },
  customer_context: {
    label: "Ügyfél-kontextus",
    explain: "Betölti a feladó korábbi ügyeit és a lehetséges ügyfél-találatokat.",
    fields: ["history_loaded", "customer_count"],
  },
  escalation_advice: {
    label: "Eszkalációs tanácsadás",
    explain: "Eldönti, kell-e supervisor-eszkaláció, és megadja az okokat.",
    fields: ["required", "reasons"],
  },
  draft_reply: {
    label: "Válasz-draft",
    explain: "Forrásokra hivatkozó válaszjavaslatot fogalmaz.",
    fields: ["format", "generation_mode", "source_count"],
  },
  verify_grounding: {
    label: "Megalapozottság ellenőrzése",
    explain: "Ellenőrzi, hogy a draft állításai a forrásokon alapulnak-e.",
    fields: ["ungrounded_count"],
  },
  iteration_cap: {
    label: "Ciklus-korlát",
    explain: "Az orchestrator elérte a megengedett lépésszámot.",
    fields: ["iterations"],
  },
```

- [ ] **Step 4: Switch Copilot.tsx to copilotChat**

`frontend/src/screens/Copilot.tsx` — a `sendMessage` `try` blokkjában az `api.agentRun(...)` hívást cseréld erre:

```typescript
      const res = await api.copilotChat({
        session_id: sessionCaseId,
        message: text,
        history: messages.map((m) => ({ role: m.role, content: m.content })),
      });

      const body = res.reply ?? "Nincs válasz.";
      const sources = res.sources ?? [];
      const generationMode = res.draft?.generation_mode;
```

(A `setLastAssistantFull(body)`, `setStreamTrigger`, `setMessages(... { role: "assistant", content: body, sources, generationMode })` sorok változatlanok.)

- [ ] **Step 5: Verify frontend type-check and build**

Run: `cd frontend; npx tsc --noEmit; npm run build`
Expected: tiszta `tsc` (nincs hiba) és sikeres build

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/agentSteps.ts frontend/src/screens/Copilot.tsx
git commit -m "Switch Copilot chat UI to the orchestrator /copilot/chat endpoint"
```

---

### Task 8: Teljes ellenőrzés

- [ ] **Step 1: Backend tesztek**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (a `test_settings_have_local_qdrant_defaults` ismert, független bukása megengedett — CLAUDE.md)

- [ ] **Step 2: PII-ellenőrzés a diffen**

Futtasd a `/pii-check` skillt a diffre (PII-egress, LLM-fallback/temperature, forrásolás, eszkaláció-auditálhatóság).

- [ ] **Step 3: Frontend ellenőrzés**

Run: `cd frontend; npx tsc --noEmit; npm run build`
Expected: tiszta

- [ ] **Step 4: Commit (ha maradt változás)**

```bash
git add -A
git commit -m "Verify Copilot orchestrator end-to-end"
```

---

## Self-Review checklist (a terv írója futtatta)

- **Spec lefedettség:** §2 subagentek → Task 2 (6 mag-subagent; a 7. "ügy-művelet" YAGNI-ból kihagyva, a meglévő "Ügy létrehozása" gomb fedi); §3 ciklus+kapuk → Task 4 (ciklus, fallback, korlát) + Task 5 (maszk/unmask kapuk); §4 kódszervezés → Task 1–7; tesztelés §6 → minden taszk TDD + Task 8.
- **Placeholder-scan:** nincs TBD/"add error handling" — minden lépésben valós kód és parancs.
- **Típus-konzisztencia:** `run_copilot_turn` kulcsai (`reply`, `sources`, `timeline`, `orchestrator_mode`) végig egyeznek az API-modellel és a frontend `CopilotChatResponse` típussal; `SUBAGENTS` kulcsai == `tools_spec.TOOLS` nevek == `STEP_META` lépésnevek; `orchestrator.run` visszaad `reply_masked`-et, amit a runner `reply`-vé alakít.
- **Megjegyzés:** a `customer_context` subagent `sender_email`-t vár; a chat-munkamenetben ez gyakran hiányzik (akkor üres kontextust ad) — ez tudatos, a Copilot session nem feltétlen kötődik feladóhoz.
