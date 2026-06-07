from __future__ import annotations

from typing import Any

from backend.eval_service import run_eval
from demo.runner import run_all_scenarios
from eval.report import load_targets


ACCEPTANCE_RULES = {
    "citation_support_rate": ("min", 0.95),
    "coverage": ("min", 0.80),
    "escalation_appropriateness": ("min", 0.90),
    "time_to_answer_ms_p95": ("max", 30000),
    "out_of_scope_answer_rate": ("max", 0.05),
    "version_mismatch": ("max", 0),
}


def _check_kpi(key: str, value: float, rule: tuple[str, float]) -> bool:
    op, target = rule
    if op == "min":
        return value >= target
    return value <= target


def run_acceptance(
    eval_limit: int = 10,
    include_edge: bool = True,
    run_demo: bool = True,
) -> dict[str, Any]:
    eval_report = run_eval(limit=eval_limit, include_edge=include_edge, save_report=True)
    kpi_values = eval_report.get("kpis", {}).get("values", {})
    kpi_checks: dict[str, Any] = {}
    kpi_failures: list[str] = []

    for key, rule in ACCEPTANCE_RULES.items():
        value = float(kpi_values.get(key, 0))
        passed = _check_kpi(key, value, rule)
        kpi_checks[key] = {"value": value, "rule": rule, "passed": passed}
        if not passed:
            kpi_failures.append(f"{key}: {value} nem felel meg ({rule[0]} {rule[1]})")

    demo_report = run_all_scenarios(save_report=True) if run_demo else {"all_passed": True, "results": []}
    demo_failures = [
        f"{item['scenario_id']}: {', '.join(item['failures'])}"
        for item in demo_report.get("results", [])
        if not item.get("passed")
    ]

    passed = not kpi_failures and demo_report.get("all_passed", False)
    return {
        "passed": passed,
        "kpi_checks": kpi_checks,
        "kpi_failures": kpi_failures,
        "demo_report": demo_report,
        "demo_failures": demo_failures,
        "eval_run_id": eval_report.get("run_id"),
        "targets": load_targets(),
        "critical_hallucination_rate": kpi_values.get("faithfulness", 0),
    }
