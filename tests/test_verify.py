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


# --- BUG 2: LLM-judge groundedness paraphrazált válaszhoz ---
import backend.verify as verify_mod
from config.settings import settings


def _enable_llm_verify(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_verify_enabled", True)


def test_verify_llm_judge_marks_paraphrase_grounded(monkeypatch):
    _enable_llm_verify(monkeypatch)
    monkeypatch.setattr(verify_mod, "chat_json", lambda s, u: {"nem_megalapozott": []})
    quote = "Az előfizető a határozatlan idejű szerződést 60 napos felmondási idővel mondhatja fel."
    draft = "A szerződés rendes felmondása két hónapos határidővel lehetséges. [S1]"
    res = verify_draft(draft, chunks=[{"chunk_id": "c1", "quote": quote}], mandatory_refs=[], citations=["c1"])
    assert res["verify_mode"] == "llm"
    assert res["ungrounded_count"] == 0
    assert res["claims"][0]["grounded"] is True


def test_verify_llm_judge_flags_unsupported(monkeypatch):
    _enable_llm_verify(monkeypatch)
    monkeypatch.setattr(verify_mod, "chat_json", lambda s, u: {"nem_megalapozott": ["c1"]})
    res = verify_draft("akármi [S1]", chunks=[{"chunk_id": "c1", "quote": "q"}], mandatory_refs=["c1"], citations=["c1"])
    assert res["verify_mode"] == "llm"
    assert res["ungrounded_count"] == 1
    assert res["missing_mandatory"] == ["c1"]


def test_verify_falls_back_to_heuristic_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    res = verify_draft("teljesen más szöveg", chunks=[{"chunk_id": "c1", "quote": "valami idézet"}], mandatory_refs=[], citations=["c1"])
    assert res["verify_mode"] == "heuristic"


def test_verify_judge_exception_falls_back_to_heuristic(monkeypatch):
    _enable_llm_verify(monkeypatch)
    def _boom(s, u):
        raise RuntimeError("api down")
    monkeypatch.setattr(verify_mod, "chat_json", _boom)
    res = verify_draft("szöveg [S1]", chunks=[{"chunk_id": "c1", "quote": "idézet"}], mandatory_refs=[], citations=["c1"])
    assert res["verify_mode"] == "heuristic"
