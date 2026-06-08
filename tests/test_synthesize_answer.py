import backend.draft as draft
from backend.draft import strip_source_markers, _build_sources
from config.settings import settings


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


_PMAP = {
    "policy_items": [
        {"chunk_id": "c1", "dok_cim": "ÁSZF", "dok_tipus": "ASZF", "paragrafus": "8.4",
         "oldalszam": 94, "idezet": "60 napos felmondási idő.", "kozertheto_magyarazat": "magy", "score": 0.9},
    ],
    "missing_mandatory": [],
}


def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")


def test_synthesize_llm_email_marks_used_sources(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "Válasz felmondás ügyben",
        "valasz": "A felmondás 60 napos határidővel lehetséges [S1].",
        "felhasznalt_forrasok": ["S1"],
        "elegtelen_fedezet": False,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "llm"
    assert result["format"] == "email"
    assert result["subject"] == "Válasz felmondás ügyben"
    assert "[S1]" in result["body_masked"]
    assert result["sources"][0]["used"] is True
    assert result["citations"] == ["c1"]


def test_synthesize_copilot_format(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "x", "valasz": "Beszédpont [S1].", "felhasznalt_forrasok": ["S1"], "elegtelen_fedezet": False,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="chat",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["format"] == "copilot"
    assert result["generation_mode"] == "llm"


def test_synthesize_strips_invalid_markers(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "x", "valasz": "Valós [S1] és kamu [S9] jelölő.",
        "felhasznalt_forrasok": ["S1", "S9"], "elegtelen_fedezet": False,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert "[S1]" in result["body_masked"]
    assert "[S9]" not in result["body_masked"]


def test_synthesize_insufficient_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "insufficient"
    assert "(forrás:" not in result["body_masked"]
    assert len(result["sources"]) == 1  # megtalált forrás megjelenik


def test_synthesize_insufficient_without_sources(monkeypatch):
    _enable_llm(monkeypatch)
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map={"policy_items": []}, actions=[],
    )
    assert result["generation_mode"] == "insufficient"
    assert result["sources"] == []


def test_synthesize_insufficient_when_llm_flags_uncovered(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "x", "valasz": "akármi", "felhasznalt_forrasok": [], "elegtelen_fedezet": True,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "insufficient"


def test_synthesize_insufficient_on_llm_exception(monkeypatch):
    _enable_llm(monkeypatch)
    def _boom(s, u):
        raise RuntimeError("api down")
    monkeypatch.setattr(draft, "chat_json", _boom)
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "insufficient"
