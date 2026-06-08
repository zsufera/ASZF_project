from backend.main import AgentRunRequest, agent_run

import agent.nodes as nodes
from agent.runner import run_agent


def test_retrieve_node_allows_semantic_path(monkeypatch):
    captured: dict = {}

    def spy(**kwargs):
        captured.update(kwargs)
        return {"chunks": [], "retrieval_mode": "hybrid_local", "result_count": 0}

    monkeypatch.setattr(nodes, "retrieve", spy)
    state = {
        "case_id": "c1",
        "classification": {"category": "egyeb"},
        "input_text": "számlázási kifogás",
    }

    nodes.retrieve_node(state)

    # Must not force the local-only path; semantic search runs when OpenAI is active.
    assert captured.get("prefer_qdrant") is not False


def _fake_retrieve(**kwargs):
    return {
        "chunks": [
            {
                "chunk_id": "one-5-1",
                "quote": "A szamlazasi kifogast az ugyfelszolgalat kivizsgalja.",
                "score": 0.9,
                "dok_tipus": "ÁSZF",
                "paragrafus": "5.1",
                "szolgaltato": "ONE",
                "dok_cim": "ONE ÁSZF",
                "oldalszam": 12,
                "cross_refs": [],
                "source_file": "one.pdf",
                "retrieval_source": "hybrid_local",
            }
        ],
        "retrieval_mode": "hybrid_local",
        "result_count": 1,
    }


def test_agent_run_completes_email_flow(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)

    result = run_agent(
        case_id="CASE-AGENT-1",
        channel="email",
        input_text="A szamlazasi kifogasom van, ugyfelszolgalat@one.hu",
        service_provider="ONE",
        output_mode="hitl",
    )

    assert result["classification"]["category"] == "szamlazas"
    assert result["draft"]["body_masked"]
    assert result["escalation"]["required"] is False
    assert result["timeline"]
    assert result["timeline"][0]["step"] == "detect_lang_type"
    assert result["timeline"][-1]["step"] == "prepare_unmask"
    assert result["draft_preview_unmasked"]["body_unmasked"]


def test_agent_run_detects_nem_panasz(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)

    result = run_agent(
        case_id="CASE-AGENT-2",
        channel="email",
        input_text_masked="Koszonom a gyors segitseget, minden rendben volt.",
        output_mode="hitl",
    )

    assert result["lang_type"]["tipus"] == "nem_panasz"
    assert result["classification"]["subtype"] == "nem_panasz"
    assert any(action["tipus"] == "koszonet_valasz" for action in result["actions"])


def test_agent_run_escalates_hatokoron_kivuli(monkeypatch) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)

    result = run_agent(
        case_id="CASE-AGENT-3",
        channel="email",
        input_text_masked="A munkahelyemen a HR panaszt tett be, nem vagyok ONE ugyfel.",
        output_mode="hitl",
    )

    assert result["lang_type"]["tipus"] == "hatokoron_kivuli"
    assert result["escalation"]["required"] is True
    assert "hatokoron_kivuli" in result["escalation"]["reasons"]


def test_agent_run_copilot_channel(monkeypatch) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)

    result = run_agent(
        case_id="CASE-AGENT-4",
        channel="phone",
        input_text_masked="A szamlazasi kifogasom van.",
        service_provider="ONE",
    )

    assert result["draft"]["format"] == "copilot"
    assert result["draft"]["body_masked"]  # nem üres
    assert "sources" in result["draft"]
    assert result["draft"]["generation_mode"] in {"llm", "insufficient"}
    assert "Beszédpontok" not in result["draft"]["body_masked"]  # régi viselkedés megszűnt


def test_agent_run_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.main.run_agent",
        lambda **kwargs: {
            "request_id": "req-1",
            "model_profile": "cloud/test",
            "prompt_version": "2026.06.07",
            "aszf_version": "2026-06-05",
            "retrieved_at": "now",
            "case_id": "CASE-API",
            "timeline": [{"step": "draft"}],
            "draft": {"body_masked": "test"},
            "escalation": {"required": False, "reasons": []},
        },
    )

    response = agent_run(
        AgentRunRequest(
            case_id="CASE-API",
            input_text_masked="Szamlazasi kerdes.",
        )
    )

    assert response["case_id"] == "CASE-API"
    assert response["draft"]["body_masked"] == "test"


def test_draft_node_uses_synthesize_for_chat(monkeypatch):
    captured = {}

    def fake_synth(**kwargs):
        captured.update(kwargs)
        return {"subject": "s", "body_masked": "Válasz [S1].",
                "sources": [{"ref": "S1", "chunk_id": "c1", "used": True}],
                "citations": ["c1"], "generation_mode": "llm", "format": "copilot",
                "disclaimer_applied": False}

    monkeypatch.setattr(nodes, "synthesize_answer", fake_synth)
    state = {
        "case_id": "c", "channel": "chat",
        "classification": {"category": "felmondas"},
        "policy_map": {"policy_items": [{"chunk_id": "c1"}]},
        "actions": [], "timeline": [],
    }
    out = nodes.draft_node(state)
    assert captured["channel"] == "chat"
    assert out["draft"]["format"] == "copilot"
    assert not out["draft"]["body_masked"].startswith("Beszédpontok:")


def test_draft_node_uses_synthesize_for_email(monkeypatch):
    captured = {}

    def fake_synth(**kwargs):
        captured.update(kwargs)
        return {"subject": "s", "body_masked": "Levél [S1].",
                "sources": [], "citations": [], "generation_mode": "llm",
                "format": "email", "disclaimer_applied": False}

    monkeypatch.setattr(nodes, "synthesize_answer", fake_synth)
    state = {
        "case_id": "c", "channel": "email",
        "classification": {"category": "szamlazas"},
        "policy_map": {"policy_items": []},
        "actions": [], "timeline": [],
    }
    out = nodes.draft_node(state)
    assert captured["channel"] == "email"
    assert out["draft"]["format"] == "email"
    assert out["timeline"][-1]["output"]["generation_mode"] == "llm"
