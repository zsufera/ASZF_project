import json

import pytest

from backend.eval_service import evaluate_single, run_eval
from eval.judge import heuristic_judge_score
from eval.metrics import (
    compute_citation_support,
    compute_faithfulness,
    compute_out_of_scope_violation,
    expected_escalation,
    kpi_status,
)
from eval.question_bank import load_question_bank
from eval.report import aggregate_kpis, compare_with_baseline, load_targets, save_baseline, save_run


def _fake_retrieve(**kwargs):
    return {
        "chunks": [
            {
                "chunk_id": "one-5-1",
                "quote": "A szamlazasi kifogast az ugyfelszolgálat kivizsgalja.",
                "paragrafus": "5.1",
                "dok_tipus": "ÁSZF",
            }
        ],
        "retrieval_mode": "hybrid_local",
        "result_count": 1,
    }


def test_question_bank_loads_samples() -> None:
    bank = load_question_bank(limit=5, include_edge=False)
    assert len(bank) == 5
    assert bank[0]["email_id"].startswith("email-")


def test_metrics_helpers() -> None:
    verify = {"claims": [{"grounded": True}, {"grounded": False}], "ungrounded_count": 1}
    assert compute_faithfulness(verify) == 0.5
    draft = {"citations": ["c1"], "body_masked": "test"}
    chunks = [{"chunk_id": "c1", "quote": "test"}]
    assert compute_citation_support(draft, chunks) is True
    assert expected_escalation({"varhato_eszkalacio": True}, {}) is True
    assert kpi_status(0.96, 0.95) == "green"


def test_evaluate_single_with_mock_retrieve(monkeypatch) -> None:
    monkeypatch.setattr("backend.eval_service.retrieve", _fake_retrieve)
    payload = {
        "email_id": "email-001-szamlazas-one",
        "torzs": "Szamlazasi kifogasom van a szamlan.",
        "varht_kategoria": "szamlazas",
        "szolgaltato": "ONE",
        "varhato_eszkalacio": False,
        "edge_case": None,
    }
    result = evaluate_single(payload)
    assert result["email_id"] == payload["email_id"]
    assert result["retrieval_support"] is True
    assert 1.0 <= result["judge_score"] <= 5.0
    assert result["time_to_answer_ms"] >= 0


def test_evaluate_single_uses_agentic_synthesis_and_citation_verify(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr("backend.eval_service.retrieve", _fake_retrieve)

    def fake_synthesize_answer(**kwargs):
        captured["synthesize"] = kwargs
        return {
            "subject": "s",
            "body_masked": "A szamlazasi kifogast kivizsgaljuk [S1].",
            "citations": ["one-5-1"],
            "sources": [{"ref": "S1", "chunk_id": "one-5-1", "used": True}],
            "generation_mode": "llm",
            "format": "email",
        }

    def fake_verify_draft(**kwargs):
        captured["verify"] = kwargs
        return {"claims": [{"grounded": True}], "ungrounded_count": 0, "warning": None}

    monkeypatch.setattr("backend.eval_service.synthesize_answer", fake_synthesize_answer, raising=False)
    monkeypatch.setattr("backend.eval_service.verify_draft", fake_verify_draft)

    payload = {
        "email_id": "email-001-szamlazas-one",
        "torzs": "Szamlazasi kifogasom van a roaming tetel miatt.",
        "varht_kategoria": "szamlazas",
        "szolgaltato": "ONE",
        "varhato_eszkalacio": False,
        "edge_case": None,
    }
    evaluate_single(payload)

    assert captured["synthesize"]["input_text_masked"] == payload["torzs"]
    assert captured["synthesize"]["channel"] == "email"
    assert captured["verify"]["citations"] == ["one-5-1"]


def test_run_eval_produces_kpis(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.eval_service.retrieve", _fake_retrieve)
    monkeypatch.setattr("eval.report.RUNS_DIR", tmp_path / "runs")
    report = run_eval(limit=3, include_edge=False, save_report=True)
    assert report["evaluated"] == 3
    assert "kpis" in report
    assert "faithfulness" in report["kpis"]["values"]
    assert (tmp_path / "runs").exists()


def test_baseline_diff(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("eval.report.BASELINE_PATH", tmp_path / "baseline.json")
    kpis = aggregate_kpis(
        [
            {
                "category_match": True,
                "citation_support": True,
                "retrieval_support": True,
                "coverage": True,
                "escalation_appropriate": True,
                "faithfulness": 1.0,
                "judge_score": 4.5,
                "time_to_answer_ms": 100,
                "out_of_scope_violation": False,
            }
        ],
        load_targets(),
    )
    save_baseline({"run_id": "base-1", "created_at": "now", "kpis": kpis})
    diff = compare_with_baseline(kpis)
    assert diff["has_baseline"] is True
