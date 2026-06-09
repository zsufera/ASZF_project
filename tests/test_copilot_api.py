from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_copilot_chat_endpoint_returns_reply_and_timeline():
    resp = client.post(
        "/copilot/chat",
        json={"session_id": "CHAT-API1", "message": "Mennyi a felmondasi ido?", "history": []},
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
