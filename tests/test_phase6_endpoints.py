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
    with TestClient(app) as test_client:
        yield test_client


def test_eval_run_returns_full_kpis(client: TestClient) -> None:
    response = client.post("/eval/run", json={"limit": 3, "include_edge": False, "save_report": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluated"] == 3
    assert "kpis" in payload
    assert "run_id" in payload
    assert "faithfulness" in payload["kpis"]["values"]


def test_eval_run_detail_and_baseline(client: TestClient) -> None:
    run = client.post("/eval/run", json={"limit": 2, "include_edge": False}).json()
    run_id = run["run_id"]
    detail = client.get(f"/eval/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["run_id"] == run_id

    saved = client.post("/eval/baseline", json={"run_id": run_id})
    assert saved.status_code == 200
    baseline = client.get("/eval/baseline")
    assert baseline.status_code == 200
    assert baseline.json()["has_baseline"] is True


def test_eval_human_score(client: TestClient) -> None:
    run = client.post("/eval/run", json={"limit": 1, "include_edge": False}).json()
    response = client.post(
        "/eval/human-score",
        json={"run_id": run["run_id"], "email_id": run["results"][0]["email_id"], "score": 4},
    )
    assert response.status_code == 200
    assert response.json()["human_score"] == 4
