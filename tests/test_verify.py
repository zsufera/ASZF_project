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


CITATION_CHUNKS = [
    {"chunk_id": "one-5-1", "quote": "A számlázási kifogást az ügyfélszolgálat kivizsgálja."},
    {"chunk_id": "one-9-2", "quote": "A felmondás harminc napos határidővel lehetséges."},
]


def test_verify_citation_grounded_when_overlap_high():
    draft = "A számlázási kifogást az ügyfélszolgálat kivizsgálja, tájékoztatjuk."
    result = verify_draft(draft, CITATION_CHUNKS, mandatory_refs=["one-5-1"], citations=["one-5-1"])
    assert result["ungrounded_count"] == 0
    assert result["missing_mandatory"] == []


def test_verify_citation_ungrounded_when_id_missing():
    draft = "Általános tájékoztatás minden részlet nélkül."
    result = verify_draft(draft, CITATION_CHUNKS, mandatory_refs=["one-5-1"], citations=["nincs-ilyen"])
    assert result["ungrounded_count"] == 1
    assert result["missing_mandatory"] == ["one-5-1"]


def test_verify_legacy_substring_when_no_citations():
    draft = "A felmondás harminc napos határidővel lehetséges."
    result = verify_draft(draft, CITATION_CHUNKS, mandatory_refs=["one-9-2"])
    assert "one-9-2" not in result["missing_mandatory"]
