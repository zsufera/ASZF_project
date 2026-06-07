from backend.policy_map import build_policy_map, load_mandatory_refs


def test_build_policy_map_turns_chunks_into_source_cards() -> None:
    chunks = [
        {
            "chunk_id": "one-3-1",
            "dok_tipus": "ÁSZF",
            "paragrafus": "3.1",
            "quote": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            "score": 1.0,
            "szolgaltato": "ONE",
            "dok_cim": "ONE ÁSZF",
            "oldalszam": 12,
        }
    ]

    result = build_policy_map(category="szamlazas", chunks=chunks)

    assert result["policy_items"] == [
        {
            "chunk_id": "one-3-1",
            "dok_tipus": "ÁSZF",
            "paragrafus": "3.1",
            "idezet": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            "kozertheto_magyarazat": "A forrás alapján ez a rész releváns a(z) szamlazas ügyhöz.",
            "dok_cim": "ONE ÁSZF",
            "oldalszam": 12,
            "score": 1.0,
        }
    ]
    expected_refs = load_mandatory_refs().get("szamlazas", [])
    assert result["mandatory_refs"] == expected_refs
    assert result["missing_mandatory"] == []


def test_build_policy_map_marks_missing_mandatory_when_no_sources() -> None:
    result = build_policy_map(category="szamlazas", chunks=[])

    expected_refs = load_mandatory_refs().get("szamlazas", [])
    assert result["policy_items"] == []
    assert result["mandatory_refs"] == expected_refs
    assert result["missing_mandatory"] == expected_refs
