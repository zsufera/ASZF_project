from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agent.runner import run_agent
from backend.tracing_service import trace_event
from demo.scenarios import SCENARIOS, DemoScenario
from eval.question_bank import load_question_bank


REPORT_DIR = Path("data/demo")


def _resolve_input(scenario: DemoScenario) -> tuple[str, str]:
    if scenario.email_id:
        for item in load_question_bank(include_edge=True, limit=100):
            if item.get("email_id") == scenario.email_id:
                return item.get("torzs", ""), f"DEMO-{scenario.scenario_id}"
    return scenario.input_text or "", f"DEMO-{scenario.scenario_id}"


def run_scenario(scenario: DemoScenario) -> dict[str, Any]:
    input_text, case_id = _resolve_input(scenario)
    started = time.perf_counter()
    result = run_agent(
        case_id=case_id,
        channel=scenario.channel,
        input_text=input_text,
        service_provider=scenario.service_provider,
        output_mode=scenario.output_mode,
        sla_expired=scenario.sla_expired,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    failures = scenario.assertions(result)
    trace_event(
        "demo_scenario",
        {"scenario_id": scenario.scenario_id, "passed": not failures, "failures": failures},
        case_id=case_id,
        duration_ms=duration_ms,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "case_id": case_id,
        "passed": not failures,
        "failures": failures,
        "duration_ms": duration_ms,
        "classification": result.get("classification"),
        "escalation": result.get("escalation"),
        "draft_format": result.get("draft", {}).get("format"),
        "chunk_count": len(result.get("retrieval", {}).get("chunks", [])),
    }


def run_all_scenarios(save_report: bool = True) -> dict[str, Any]:
    results = [run_scenario(scenario) for scenario in SCENARIOS]
    passed = sum(1 for item in results if item["passed"])
    report = {
        "scenarios_run": len(results),
        "scenarios_passed": passed,
        "all_passed": passed == len(results),
        "results": results,
    }
    if save_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / "latest_demo_report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
