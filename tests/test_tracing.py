from backend.tracing_service import list_recent_traces, trace_event


def test_trace_event_persists_and_lists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.tracing_service.TRACE_DIR", tmp_path)
    trace_event("test_span", {"ok": True}, case_id="CASE-T1", duration_ms=12)
    traces = list_recent_traces(limit=5)
    assert len(traces) == 1
    assert traces[0]["name"] == "test_span"
    assert traces[0]["case_id"] == "CASE-T1"
