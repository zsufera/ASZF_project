import pytest
from fastapi.testclient import TestClient

from backend.auth import ensure_users_in_db
from backend.db import init_db
from backend.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "phase4.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.auth.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.runner.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.history.settings.sqlite_path", str(db_path))
    monkeypatch.setattr(
        "agent.nodes.retrieve",
        lambda **kwargs: {
            "chunks": [{"chunk_id": "c1", "quote": "szamlazas", "paragrafus": "1", "dok_tipus": "ÁSZF"}],
            "result_count": 1,
        },
    )
    init_db()
    ensure_users_in_db()
    with TestClient(app) as test_client:
        yield test_client


def test_auth_login_endpoint(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "ui_demo", "password": "ui_demo"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "ui"
    assert payload.get("user_id")


def test_inbox_endpoint_returns_items(client: TestClient) -> None:
    response = client.post("/cases/seed", json={"force": True})
    assert response.status_code == 200
    inbox = client.get("/inbox")
    assert inbox.status_code == 200
    payload = inbox.json()
    assert payload["count"] >= 1
    assert payload["items"][0]["case_id"].startswith("CASE-")


def test_case_create_and_detail(client: TestClient) -> None:
    created = client.post(
        "/cases/create",
        json={"channel": "email", "input_text": "Teszt kerdes a szamlazasrol."},
    )
    assert created.status_code == 200
    case_id = created.json()["case_id"]

    detail = client.get(f"/cases/{case_id}")
    assert detail.status_code == 200
    assert detail.json()["case_id"] == case_id


def test_case_process_endpoint(client: TestClient) -> None:
    created = client.post(
        "/cases/create",
        json={"channel": "email", "input_text": "Szamlazasi kifogas."},
    )
    case_id = created.json()["case_id"]
    processed = client.post(
        "/cases/process",
        json={"case_id": case_id, "output_mode": "hitl", "username": "ui_demo"},
    )
    assert processed.status_code == 200
    body = processed.json()
    assert body.get("draft")
    assert body.get("timeline")


def test_supervisor_endpoints(client: TestClient) -> None:
    client.post("/cases/seed", json={"force": True})
    queue = client.get("/supervisor/queue")
    stats = client.get("/supervisor/stats")
    assert queue.status_code == 200
    assert stats.status_code == 200
    assert "total_cases" in stats.json()
