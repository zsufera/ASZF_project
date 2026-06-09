from agent.copilot import orchestrator, tools_spec
from agent.copilot.session import CopilotSession
from agent.copilot.subagents import SUBAGENTS


def test_tools_spec_matches_subagent_registry():
    spec_names = {tool["name"] for tool in tools_spec.TOOLS}
    assert spec_names == set(SUBAGENTS)


def test_tools_prompt_lists_every_tool():
    prompt = tools_spec.tools_prompt()
    for tool in tools_spec.TOOLS:
        assert tool["name"] in prompt


def test_orchestrator_fallback_path_when_no_llm():
    session = CopilotSession(session_id="CHAT-O1", message_masked="Mennyi a felmondasi ido?")
    result = orchestrator.run(session)
    assert result["orchestrator_mode"] == "fallback"
    assert isinstance(result["reply_masked"], str) and result["reply_masked"]
    steps = [entry["step"] for entry in result["timeline"]]
    assert "knowledge_search" in steps


def test_orchestrator_llm_loop_calls_chosen_tools(monkeypatch):
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: True)
    scripted = [
        {"action": "call_tool", "tool": "knowledge_search", "args": {"category": "szerzodesfelmondas_modositas"}},
        {"action": "respond", "reply": "A felmondasi ido a forras szerint 30 nap. [S1]"},
    ]
    calls = {"i": 0}

    def fake_decide(system, user):
        out = scripted[calls["i"]]
        calls["i"] += 1
        return out

    monkeypatch.setattr("agent.copilot.orchestrator.chat_json", fake_decide)
    session = CopilotSession(session_id="CHAT-O2", message_masked="Mennyi a felmondasi ido?")
    result = orchestrator.run(session)
    assert result["orchestrator_mode"] == "llm"
    assert "30 nap" in result["reply_masked"]
    assert any(entry["step"] == "knowledge_search" for entry in result["timeline"])


def test_orchestrator_accepts_tool_name_as_action(monkeypatch):
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: True)
    scripted = [
        {"action": "classify", "args": {}},
        {"action": "respond", "reply": "Besoroltam."},
    ]
    calls = {"i": 0}

    def fake_decide(system, user):
        out = scripted[calls["i"]]
        calls["i"] += 1
        return out

    monkeypatch.setattr("agent.copilot.orchestrator.chat_json", fake_decide)
    session = CopilotSession(session_id="CHAT-O4", message_masked="Nincs internetem napok ota")
    result = orchestrator.run(session)
    assert result["reply_masked"] == "Besoroltam."
    assert any(entry["step"] == "classify" for entry in result["timeline"])


def test_orchestrator_invalid_llm_decision_falls_back(monkeypatch):
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: True)
    monkeypatch.setattr(
        "agent.copilot.orchestrator.chat_json",
        lambda system, user: {"action": "nonsense"},
    )
    session = CopilotSession(session_id="CHAT-O5", message_masked="Mennyi a felmondasi ido?")
    result = orchestrator.run(session)
    assert result["orchestrator_mode"] == "fallback"
    assert any(entry["step"] == "knowledge_search" for entry in result["timeline"])


def test_fallback_drafts_even_when_escalation_required(monkeypatch):
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: False)
    session = CopilotSession(session_id="CHAT-O6", message_masked="Mennyi a felmondasi ido?")
    result = orchestrator.run(session)
    steps = [entry["step"] for entry in result["timeline"]]
    assert "escalation_advice" in steps
    assert "draft_reply" in steps
    assert "Nincs elegendo ASZF-fedezet" not in result["reply_masked"]


def test_orchestrator_respects_iteration_cap(monkeypatch):
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: True)
    monkeypatch.setattr(
        "agent.copilot.orchestrator.chat_json",
        lambda system, user: {"action": "call_tool", "tool": "classify", "args": {}},
    )
    session = CopilotSession(session_id="CHAT-O3", message_masked="bla")
    result = orchestrator.run(session)
    tool_steps = [entry for entry in result["timeline"] if entry["step"] == "classify"]
    assert len(tool_steps) <= orchestrator.MAX_ITERATIONS
    assert result["reply_masked"]
