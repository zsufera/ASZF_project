from backend.verify import verify_draft


def test_verify_draft_marks_supported_source_quotes() -> None:
    result = verify_draft(
        draft_body_masked="A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
        chunks=[
            {
                "chunk_id": "one-3-1",
                "quote": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            }
        ],
        mandatory_refs=["one-3-1"],
    )

    assert result["ungrounded_count"] == 0
    assert result["claims"] == [
        {
            "claim": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            "grounded": True,
            "chunk_id": "one-3-1",
        }
    ]
    assert result["missing_mandatory"] == []
    assert result["warning"] is None


def test_verify_draft_flags_missing_source_and_mandatory_ref() -> None:
    result = verify_draft(
        draft_body_masked="Forrással nem fedezett állítás.",
        chunks=[{"chunk_id": "one-3-1", "quote": "Másik forrásidézet."}],
        mandatory_refs=["one-3-1"],
    )

    assert result["ungrounded_count"] == 1
    assert result["missing_mandatory"] == ["one-3-1"]
    assert result["warning"] == "A draft nem teljesen forrásolt vagy kötelező hivatkozás hiányzik."
