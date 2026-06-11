from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.metadata import PROMPT_VERSION, load_manifest_summary
from eval.metrics import kpi_status


TARGETS_PATH = Path("config/eval_targets.yaml")
RUNS_DIR = Path("data/eval/runs")
BASELINE_PATH = Path("data/eval/baseline.json")
HUMAN_SCORES_PATH = Path("data/eval/human_scores.json")


def load_targets(path: Path = TARGETS_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload.get("targets", {})


def aggregate_kpis(results: list[dict[str, Any]], targets: dict[str, Any]) -> dict[str, Any]:
    total = len(results) or 1
    manifest = load_manifest_summary()

    def rate(key: str) -> float:
        return round(sum(1 for row in results if row.get(key)) / total, 3)

    def avg(key: str) -> float:
        values = [float(row[key]) for row in results if row.get(key) is not None]
        return round(sum(values) / len(values), 3) if values else 0.0

    out_of_scope = rate("out_of_scope_violation")
    kpis = {
        "faithfulness": avg("faithfulness"),
        "citation_support_rate": rate("citation_support"),
        "judge_score": avg("judge_score"),
        "retrieval_support": rate("retrieval_support"),
        "coverage": rate("coverage"),
        "escalation_appropriateness": rate("escalation_appropriate"),
        "time_to_answer_ms_p95": sorted(row.get("time_to_answer_ms", 0) for row in results)[
            max(0, int(total * 0.95) - 1)
        ],
        "category_accuracy": rate("category_match"),
        "out_of_scope_answer_rate": out_of_scope,
        "version_mismatch": 0,
        "audit_completeness": 1.0,
        "prompt_version": PROMPT_VERSION,
        "aszf_version": manifest.get("aszf_version"),
    }

    llm_scores = [
        float(row["llm_judge_score"]) for row in results if row.get("llm_judge_score") is not None
    ]
    if llm_scores:
        kpis["llm_judge_score"] = round(sum(llm_scores) / len(llm_scores), 2)
        kpis["llm_judge_coverage"] = round(len(llm_scores) / total, 3)

    status: dict[str, str] = {}
    kpis["time_to_answer_ms"] = kpis["time_to_answer_ms_p95"]
    for key, target in targets.items():
        if key not in kpis and key != "out_of_scope_answer_rate_max" and key != "version_mismatch_max":
            continue
        value = kpis.get(key, kpis.get("time_to_answer_ms_p95"))
        if key == "time_to_answer_ms":
            status[key] = kpi_status(float(kpis["time_to_answer_ms_p95"]), float(target), higher_is_better=False)
        elif key == "out_of_scope_answer_rate_max":
            status["out_of_scope_answer_rate"] = kpi_status(value, target, higher_is_better=False)
        elif key == "version_mismatch_max":
            status["version_mismatch"] = "green" if value <= target else "red"
        else:
            status[key] = kpi_status(float(value), float(target), higher_is_better=True)

    return {"values": kpis, "targets": targets, "status": status}


def compare_with_baseline(kpis: dict[str, Any], baseline_path: Path | None = None) -> dict[str, Any]:
    target = baseline_path or BASELINE_PATH
    if not target.exists():
        return {"has_baseline": False, "diff": {}}
    baseline = json.loads(target.read_text(encoding="utf-8"))
    current = kpis.get("values", {})
    previous = baseline.get("kpis", {}).get("values", baseline.get("values", {}))
    diff: dict[str, Any] = {}
    for key, value in current.items():
        if key in previous and isinstance(value, (int, float)) and isinstance(previous[key], (int, float)):
            diff[key] = round(float(value) - float(previous[key]), 3)
    return {
        "has_baseline": True,
        "baseline_run_id": baseline.get("run_id"),
        "baseline_created_at": baseline.get("created_at"),
        "diff": diff,
    }


def save_run(report: dict[str, Any], runs_dir: Path | None = None) -> str:
    target_dir = runs_dir or RUNS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    run_id = report.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report["run_id"] = run_id
    path = target_dir / f"{run_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_id


def save_baseline(report: dict[str, Any], baseline_path: Path | None = None) -> dict[str, Any]:
    target = baseline_path or BASELINE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": report.get("run_id"),
        "created_at": report.get("created_at"),
        "kpis": report.get("kpis"),
        "prompt_version": report.get("prompt_version"),
        "aszf_version": report.get("aszf_version"),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_baseline(baseline_path: Path | None = None) -> dict[str, Any] | None:
    target = baseline_path or BASELINE_PATH
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def load_run(run_id: str, runs_dir: Path | None = None) -> dict[str, Any] | None:
    target_dir = runs_dir or RUNS_DIR
    path = target_dir / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_human_score(run_id: str, email_id: str, score: int) -> dict[str, Any]:
    HUMAN_SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    if HUMAN_SCORES_PATH.exists():
        payload = json.loads(HUMAN_SCORES_PATH.read_text(encoding="utf-8"))
    payload.setdefault(run_id, {})[email_id] = score
    HUMAN_SCORES_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"run_id": run_id, "email_id": email_id, "human_score": score}
