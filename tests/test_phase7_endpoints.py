import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.eval_service.retrieve",
        lambda **kwargs: {
            "chunks": [{"chunk_id": "c1", "quote": "szamlazas kifogas", "paragrafus": "1", "dok_tipus": "ÁSZF"}],
            "result_count": 1,
            "retrieval_mode": "hybrid_local",
        },
    )
    monkeypatch.setattr("eval.report.RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr("eval.report.BASELINE_PATH", tmp_path / "baseline.json")
    monkeypatch.setattr("demo.runner.REPORT_DIR", tmp_path / "demo")
    monkeypatch.setattr(
        "agent.nodes.retrieve",
        lambda **kwargs: {
            "chunks": [{"chunk_id": "c1", "quote": "szamlazas", "paragrafus": "1", "dok_tipus": "ÁSZF"}],
            "result_count": 1,
            "retrieval_mode": "hybrid_local",
        },
    )
    monkeypatch.setattr("backend.tracing_service.TRACE_DIR", tmp_path / "traces")
    with TestClient(app) as test_client:
        yield test_client


def test_demo_run_endpoint(client: TestClient) -> None:
    response = client.post("/demo/run", json={"save_report": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenarios_run"] == 4
    assert "all_passed" in payload


def test_acceptance_run_endpoint(client: TestClient) -> None:
    response = client.post("/acceptance/run", json={"eval_limit": 3, "include_edge": False, "run_demo": True})
    assert response.status_code == 200
    payload = response.json()
    assert "passed" in payload
    assert "kpi_checks" in payload
    assert "demo_report" in payload


def test_observability_traces_endpoint(client: TestClient) -> None:
    client.post("/demo/run", json={"save_report": False})
    response = client.get("/observability/traces?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
