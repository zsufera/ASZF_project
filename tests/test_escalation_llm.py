import backend.escalation as escalation


def test_merge_escalation_can_only_raise():
    rule = {"required": False, "reasons": []}
    # LLM suggests escalation -> required becomes True
    raised = escalation.merge_escalation(rule, {"suggested": True, "okok": ["gyanus_ugy"]})
    assert raised["required"] is True
    assert "gyanus_ugy" in raised["reasons"]
    assert "llm_javaslat" in raised["reasons"]
    assert raised["llm_reasoning"]


def test_merge_escalation_never_lowers():
    rule = {"required": True, "reasons": ["sla_lejart"]}
    # LLM does NOT suggest -> required stays True, reasons preserved
    merged = escalation.merge_escalation(rule, {"suggested": False, "okok": []})
    assert merged["required"] is True
    assert merged["reasons"] == ["sla_lejart"]
    assert merged["llm_reasoning"] is None
