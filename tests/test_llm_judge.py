"""LLM judge: offline returns None, stubbed LLM returns a score."""
import eval.llm_judge as llm_judge
from config.settings import settings

CHUNKS = [{"chunk_id": "one-5-1", "quote": "A szamlazasi kifogast kivizsgaljuk."}]


def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_judge_enabled", True)


def test_offline_returns_none() -> None:
    assert llm_judge.llm_judge_review("kerdes", "draft", CHUNKS) is None


def test_valid_output_returns_clamped_score(monkeypatch) -> None:
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        llm_judge,
        "chat_json",
        lambda system, user: {
            "pontszam": 4.2,
            "forrashuseg": 5,
            "teljesseg": 4,
            "hangnem": 4,
            "kozerthetoseg": 4,
            "indoklas": "Forrasolt, udvarias.",
        },
    )
    result = llm_judge.llm_judge_review(
        "Szamlazasi kifogasom van.", "Tisztelt Ugyfelunk! ...", CHUNKS
    )
    assert result is not None
    assert result["score"] == 4.2
    assert result["judge_mode"] == "llm"
    assert result["dimensions"]["forrashuseg"] == 5.0


def test_score_above_five_is_clamped(monkeypatch) -> None:
    _enable_llm(monkeypatch)
    monkeypatch.setattr(
        llm_judge,
        "chat_json",
        lambda system, user: {"pontszam": 9.0, "indoklas": "tul magas"},
    )
    result = llm_judge.llm_judge_review("kerdes", "draft", CHUNKS)
    assert result is not None
    assert result["score"] == 5.0


def test_invalid_output_falls_back_to_none(monkeypatch) -> None:
    _enable_llm(monkeypatch)
    monkeypatch.setattr(llm_judge, "chat_json", lambda system, user: {"pontszam": "kivalo"})
    assert llm_judge.llm_judge_review("kerdes", "draft", CHUNKS) is None


def test_disabled_flag_returns_none(monkeypatch) -> None:
    _enable_llm(monkeypatch)
    monkeypatch.setattr(settings, "llm_judge_enabled", False)
    assert llm_judge.llm_judge_review("kerdes", "draft", CHUNKS) is None


def test_empty_draft_returns_none(monkeypatch) -> None:
    _enable_llm(monkeypatch)
    assert llm_judge.llm_judge_review("kerdes", "   ", CHUNKS) is None


def test_aggregate_includes_llm_judge_when_present() -> None:
    from eval.report import aggregate_kpis

    results = [
        {"llm_judge_score": 4.0, "time_to_answer_ms": 100},
        {"llm_judge_score": 5.0, "time_to_answer_ms": 100},
        {"llm_judge_score": None, "time_to_answer_ms": 100},
    ]
    kpis = aggregate_kpis(results, targets={})
    assert kpis["values"]["llm_judge_score"] == 4.5
    assert kpis["values"]["llm_judge_coverage"] == 0.667


def test_aggregate_omits_llm_judge_when_absent() -> None:
    from eval.report import aggregate_kpis

    results = [{"time_to_answer_ms": 100}]
    kpis = aggregate_kpis(results, targets={})
    assert "llm_judge_score" not in kpis["values"]
