from agent.copilot.runner import run_copilot_turn


def test_runner_masks_input_and_never_leaks_pii_to_timeline():
    raw = "Az email cimem kovacs.janos@example.com, mennyi a felmondasi ido?"
    out = run_copilot_turn(session_id="CHAT-R1", message=raw, history=[])
    serialized = str(out["timeline"])
    assert "kovacs.janos@example.com" not in serialized
    assert "reply" in out
    assert "orchestrator_mode" in out


def test_runner_strips_source_markers_from_customer_facing_reply(monkeypatch):
    monkeypatch.setattr(
        "agent.copilot.orchestrator.run",
        lambda session: {
            "reply_masked": "A felmondasi ido 30 nap. [S1]",
            "sources": [],
            "draft": None,
            "escalation": None,
            "timeline": [],
            "orchestrator_mode": "fallback",
        },
    )
    out = run_copilot_turn(
        session_id="CHAT-R2",
        message="Kerek egy ugyfelnek kuldheto valaszt a felmondasi idorol.",
        history=[],
        customer_facing=True,
    )
    assert "[S" not in out["reply"]
