from backend.draft import strip_source_markers, _build_sources


def test_strip_source_markers_removes_tokens_and_normalizes():
    text = "A felmondás 60 napos [S1] . A kedvezmény visszafizetése [S2] is releváns."
    assert strip_source_markers(text) == "A felmondás 60 napos. A kedvezmény visszafizetése is releváns."


def test_strip_source_markers_handles_empty():
    assert strip_source_markers("") == ""
    assert strip_source_markers(None) == ""


def test_build_sources_assigns_sequential_refs():
    policy_items = [
        {"chunk_id": "c1", "dok_cim": "ÁSZF", "dok_tipus": "ASZF", "paragrafus": "8.4",
         "oldalszam": 94, "idezet": "idézet1", "kozertheto_magyarazat": "magy1", "score": 0.8},
        {"chunk_id": "c2", "idezet": "idézet2"},
    ]
    sources = _build_sources(policy_items)
    assert [s["ref"] for s in sources] == ["S1", "S2"]
    assert sources[0]["dok_cim"] == "ÁSZF"
    assert sources[0]["magyarazat"] == "magy1"
    assert sources[0]["used"] is False
    assert sources[1]["chunk_id"] == "c2"


def test_build_sources_skips_items_without_chunk_id():
    sources = _build_sources([{"idezet": "x"}, {"chunk_id": "c1", "idezet": "y"}])
    assert [s["ref"] for s in sources] == ["S1"]
    assert sources[0]["chunk_id"] == "c1"


def test_strip_source_markers_multiline_no_orphan_whitespace():
    text = "Tisztelt Ügyfelünk!\n\nA felmondás 60 napos [S1]\nhatáridővel lehetséges.\n\nÜdvözlettel"
    out = strip_source_markers(text)
    # nincs sor eleji/sor végi szóköz, és nincs jelölő
    assert "[S1]" not in out
    for line in out.split("\n"):
        assert line == line.strip()
    # az értelmes tartalom megmarad
    assert "A felmondás 60 napos" in out
    assert "határidővel lehetséges." in out
