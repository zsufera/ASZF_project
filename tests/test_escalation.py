from backend.escalation import decide_escalation


def test_decide_escalation_for_low_confidence() -> None:
    result = decide_escalation(
        confidence=0.4,
        confidence_threshold=0.75,
        is_repeated=False,
        missing_mandatory=[],
        sla_expired=False,
        trigger_hits=[],
    )

    assert result["required"] is True
    assert "alacsony_konfidencia" in result["reasons"]


def test_decide_escalation_for_missing_policy_coverage() -> None:
    result = decide_escalation(
        confidence=0.9,
        confidence_threshold=0.75,
        is_repeated=False,
        missing_mandatory=["kötelező hivatkozás"],
        sla_expired=False,
        trigger_hits=[],
    )

    assert result["required"] is True
    assert "hianyzo_kotelezo_hivatkozas" in result["reasons"]


def test_decide_escalation_not_required_for_clean_case() -> None:
    result = decide_escalation(
        confidence=0.9,
        confidence_threshold=0.75,
        is_repeated=False,
        missing_mandatory=[],
        sla_expired=False,
        trigger_hits=[],
    )

    assert result == {"required": False, "reasons": []}
