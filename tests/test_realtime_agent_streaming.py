from fastapi.testclient import TestClient

from backend.auth import ensure_users_in_db
from backend.case_service import create_ad_hoc_case
from backend.db import init_db
from backend.main import app
from agent.runner import run_agent


def _fake_retrieve(**kwargs):
    return {
        "chunks": [{"chunk_id": "c1", "quote": "szamlazas", "paragrafus": "1", "dok_tipus": "ASZF"}],
        "result_count": 1,
        "retrieval_mode": "hybrid_local",
        "unresolved_refs": [],
    }


def test_run_agent_emits_timeline_steps_through_callback(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "stream.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.runner.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)
    monkeypatch.setattr("backend.tracing_service.TRACE_DIR", tmp_path / "traces")

    emitted: list[dict] = []
    result = run_agent(
        case_id="CASE-CB",
        channel="email",
        input_text="Szamlazasi kerdes.",
        on_timeline_step=emitted.append,
    )

    assert emitted
    assert emitted[0]["step"] == "detect_lang_type"
    assert [step["step"] for step in emitted] == [step["step"] for step in result["timeline"]]


def test_copilot_chat_stream_returns_realtime_step_events(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "copilot-stream.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.copilot.orchestrator.llm_available", lambda: False)
    monkeypatch.setattr("backend.tracing_service.TRACE_DIR", tmp_path / "traces")

    with TestClient(app) as client:
        response = client.post(
            "/copilot/chat/stream",
            json={"session_id": "CHAT-STREAM-1", "message": "Mennyi a felmondasi ido?", "history": []},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: step" in response.text
    assert "event: complete" in response.text
    assert '"timeline"' in response.text


def test_case_process_stream_returns_realtime_step_events(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "case-stream.db"
    for target in [
        "config.settings.settings.sqlite_path",
        "backend.case_service.settings.sqlite_path",
        "backend.services.case_processing.settings.sqlite_path",
        "backend.audit_service.settings.sqlite_path",
        "backend.masking.settings.sqlite_path",
        "backend.auth.settings.sqlite_path",
        "agent.runner.settings.sqlite_path",
    ]:
        monkeypatch.setattr(target, str(db_path))
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)
    monkeypatch.setattr("backend.tracing_service.TRACE_DIR", tmp_path / "traces")
    init_db()
    ensure_users_in_db()
    case_id = create_ad_hoc_case(channel="email", input_text="Szamlazasi kerdes.", service_provider="ONE")

    with TestClient(app) as client:
        response = client.post(
            "/cases/process/stream",
            json={"case_id": case_id, "output_mode": "hitl", "username": "ui_demo"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: step" in response.text
    assert "event: complete" in response.text
