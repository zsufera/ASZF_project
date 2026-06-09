from backend import llm_tasks


def test_classify_task_offline_returns_rule_mode():
    out = llm_tasks.classify_message_task("Szamlazasi hibam van", history_summary_masked=None)
    assert out["error"] is None
    assert out["mode"] == "rule"
    assert out["result"]["category"] == "szamlazas"


def test_verify_task_wraps_result_and_mode():
    chunks = [{"chunk_id": "c1", "quote": "A felmondasi ido 30 nap."}]
    out = llm_tasks.verify_grounding_task(
        draft_body_masked="A felmondasi ido 30 nap. [S1]",
        chunks=chunks,
        mandatory_refs=[],
        citations=["c1"],
    )
    assert out["error"] is None
    assert out["mode"] in {"llm", "heuristic"}
    assert "ungrounded_count" in out["result"]
