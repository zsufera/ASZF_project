import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.auth import ensure_users_in_db
from backend.db import init_db
from backend.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "tier2.db"
    for target in [
        "config.settings.settings.sqlite_path",
        "backend.case_service.settings.sqlite_path",
        "backend.audit_service.settings.sqlite_path",
        "backend.masking.settings.sqlite_path",
        "backend.auth.settings.sqlite_path",
        "agent.runner.settings.sqlite_path",
    ]:
        monkeypatch.setattr(target, str(db_path))
    monkeypatch.setattr("backend.tracing_service.TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(
        "agent.nodes.retrieve",
        lambda **kwargs: {
            "chunks": [{"chunk_id": "c1", "quote": "szamlazas", "paragrafus": "1", "dok_tipus": "ÁSZF"}],
            "result_count": 1,
            "retrieval_mode": "hybrid_local",
            "unresolved_refs": [],
        },
    )
    init_db()
    ensure_users_in_db()
    with TestClient(app) as test_client:
        yield test_client


def test_agent_run_stream_returns_sse_events(client: TestClient) -> None:
    response = client.post(
        "/agent/run/stream",
        json={"case_id": "CASE-STREAM", "channel": "email", "input_text": "Szamlazasi kerdes."},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: step" in body
    assert "event: complete" in body


def test_supervisor_claim_assign_release_contract(client: TestClient) -> None:
    created = client.post("/cases/create", json={"channel": "email", "input_text": "Surgos panasz."})
    case_id = created.json()["case_id"]

    claim = client.post("/cases/claim", json={"case_id": case_id, "username": "supervisor_demo"})
    assert claim.status_code == 200
    assert claim.json()["claimed_by_username"] == "supervisor_demo"

    assign = client.post(
        "/cases/assign",
        json={"case_id": case_id, "assignee_username": "ui_demo", "username": "supervisor_demo"},
    )
    assert assign.status_code == 200
    assert assign.json()["assignee_username"] == "ui_demo"

    detail = client.get(f"/cases/{case_id}").json()
    assert detail["claimed_by_username"] == "supervisor_demo"
    assert detail["assignee_username"] == "ui_demo"

    release = client.post("/cases/release", json={"case_id": case_id, "username": "supervisor_demo"})
    assert release.status_code == 200
    assert release.json()["claimed_by_username"] is None


def test_copilot_session_and_handoff_contract(client: TestClient) -> None:
    session_id = "CHAT-TIER2"
    turn = client.post(
        "/copilot/sessions/turn",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "Mennyi a felmondasi ido?",
            "username": "ui_demo",
        },
    )
    assert turn.status_code == 200

    sessions = client.get("/copilot/sessions", params={"username": "ui_demo"})
    assert sessions.status_code == 200
    assert any(item["session_id"] == session_id for item in sessions.json()["items"])

    handoff = client.post(
        "/copilot/sessions/handoff",
        json={"session_id": session_id, "username": "ui_demo", "selected_turn_ids": []},
    )
    assert handoff.status_code == 200
    assert handoff.json()["case_id"].startswith("CASE-ADHOC-")
