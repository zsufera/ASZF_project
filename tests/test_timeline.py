from backend.timeline import timeline_entry


def test_timeline_entry_is_superset_of_legacy_shape():
    entry = timeline_entry(
        "classify",
        output={"category": "szamlazas"},
        mode="llm",
        status="ok",
        counts={"candidates": 2},
        summary="Szamlazas, 89% konfidencia",
    )
    assert entry["step"] == "classify"
    assert entry["output"] == {"category": "szamlazas"}
    assert entry["mode"] == "llm"
    assert entry["status"] == "ok"
    assert entry["counts"] == {"candidates": 2}
    assert entry["warnings"] == []
    assert entry["summary"] == "Szamlazas, 89% konfidencia"


def test_timeline_entry_defaults():
    entry = timeline_entry("mask_input", output={"token_count": 3})
    assert entry["mode"] == "rule"
    assert entry["status"] == "ok"
    assert entry["counts"] == {}
    assert entry["warnings"] == []
    assert entry["summary"] == ""
