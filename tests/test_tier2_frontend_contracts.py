from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_frontend_api_exposes_tier2_contracts() -> None:
    api = read("frontend/src/lib/api.ts")
    assert "streamAgentRun" in api
    assert "/agent/run/stream" in api
    assert "claimCase" in api
    assert "/cases/claim" in api
    assert "assignCase" in api
    assert "/cases/assign" in api
    assert "releaseCase" in api
    assert "/cases/release" in api
    assert "getCopilotSessions" in api
    assert "/copilot/sessions" in api
    assert "recordCopilotTurn" in api
    assert "handoffCopilotSession" in api


def test_supervisor_renders_assignment_and_sla_controls() -> None:
    supervisor = read("frontend/src/screens/Supervisor.tsx")
    assert "SlaCountdown" in supervisor
    assert "claimCase" in supervisor
    assert "assignCase" in supervisor
    assert "releaseCase" in supervisor
    assert "claimed_by_username" in supervisor
    assert "assignee_username" in supervisor


def test_copilot_renders_session_handoff_controls() -> None:
    copilot = read("frontend/src/screens/Copilot.tsx")
    assert "CopilotSessionList" in copilot
    assert "getCopilotSessions" in copilot
    assert "recordCopilotTurn" in copilot
    assert "handoffCopilotSession" in copilot
