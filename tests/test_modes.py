from backend.modes import (
    ClassifyMode,
    EscalationMode,
    GenerationMode,
    OrchestratorMode,
    VerifyMode,
)


def test_modes_are_str_backward_compatible():
    assert ClassifyMode.LLM == "llm"
    assert ClassifyMode.RULE == "rule"
    assert GenerationMode.LLM == "llm"
    assert GenerationMode.TEMPLATE == "template"
    assert GenerationMode.INSUFFICIENT == "insufficient"
    assert VerifyMode.LLM == "llm"
    assert VerifyMode.HEURISTIC == "heuristic"
    assert EscalationMode.RULE == "rule"
    assert EscalationMode.RULE_LLM == "rule+llm"
    assert OrchestratorMode.LLM == "llm"
    assert OrchestratorMode.FALLBACK == "fallback"


def test_mode_json_serializes_as_plain_string():
    import json

    assert json.dumps({"m": GenerationMode.LLM}) == '{"m": "llm"}'
