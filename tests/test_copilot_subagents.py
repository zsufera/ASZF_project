from agent.copilot import subagents
from agent.copilot.session import CopilotSession


def test_session_holds_masked_text_and_accumulates_timeline():
    session = CopilotSession(session_id="CHAT-1", message_masked="Szamlazasi hibam van [MASK_NAME_1]")
    assert session.session_id == "CHAT-1"
    assert session.timeline == []
    session.record(step="classify", output={"category": "szamlazas"}, mode="rule", summary="szamlazas")
    assert len(session.timeline) == 1
    assert session.timeline[0]["step"] == "classify"
    assert session.timeline[0]["summary"] == "szamlazas"


def test_knowledge_search_populates_retrieval_and_timeline():
    session = CopilotSession(session_id="CHAT-2", message_masked="Mennyi a felmondasi ido?")
    obs = subagents.knowledge_search(session, category="szerzodesfelmondas_modositas")
    assert session.retrieval is not None
    assert "result_count" in obs
    assert any(entry["step"] == "knowledge_search" for entry in session.timeline)


def test_classify_subagent_sets_classification():
    session = CopilotSession(session_id="CHAT-3", message_masked="Nincs internetem napok ota")
    obs = subagents.classify(session)
    assert session.classification["category"] == "hibabejelentes_szolgaltataskieses"
    assert obs["category"] == "hibabejelentes_szolgaltataskieses"
    assert any(entry["step"] == "classify" for entry in session.timeline)


def test_draft_reply_requires_retrieval_first():
    session = CopilotSession(session_id="CHAT-4", message_masked="Mennyi a felmondasi ido?")
    subagents.knowledge_search(session, category="szerzodesfelmondas_modositas")
    obs = subagents.draft_reply(session, category="szerzodesfelmondas_modositas")
    assert session.draft is not None
    assert "generation_mode" in obs
    assert any(entry["step"] == "draft_reply" for entry in session.timeline)


def test_subagents_registry_contains_all_tools():
    assert set(subagents.SUBAGENTS) == {
        "classify",
        "knowledge_search",
        "customer_context",
        "escalation_advice",
        "draft_reply",
        "verify_grounding",
    }
