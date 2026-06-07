from demo.runner import run_all_scenarios, run_scenario
from demo.scenarios import SCENARIOS


def _fake_retrieve(**kwargs):
    return {
        "chunks": [
            {
                "chunk_id": "one-5-1",
                "quote": "A szamlazasi kifogast az ugyfelszolgalat kivizsgalja.",
                "score": 0.9,
                "dok_tipus": "ÁSZF",
                "paragrafus": "5.1",
                "szolgaltato": "ONE",
            }
        ],
        "retrieval_mode": "hybrid_local",
        "result_count": 1,
    }


def test_demo_scenarios_all_pass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)
    monkeypatch.setattr("demo.runner.REPORT_DIR", tmp_path)

    report = run_all_scenarios(save_report=True)
    assert report["scenarios_run"] == len(SCENARIOS)
    assert report["all_passed"] is True
    assert (tmp_path / "latest_demo_report.json").exists()


def test_egyedi_szerzodes_scenario_escalates(monkeypatch) -> None:
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)
    scenario = next(item for item in SCENARIOS if item.scenario_id == "egyedi_szerzodes_eszkalacio")
    result = run_scenario(scenario)
    assert result["passed"] is True
    assert "egyedi_szerzodes_gyanu" in str(result.get("escalation", {}))
