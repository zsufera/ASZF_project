from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

from fastapi.routing import APIRoute

import backend.draft as draft
from backend.main import app


ROOT = Path(__file__).resolve().parents[1]


def _route(path: str, method: str) -> APIRoute:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def test_runtime_and_diagnostics_are_out_of_review_noise() -> None:
    assert not list(ROOT.glob("_diag_*.py"))
    assert (ROOT / "scripts" / "diagnostics").is_dir()

    ignored_paths = [
        "data/traces/trace-local.jsonl",
        "data/derived/derive_report.json",
        ".pytest_cache/v/cache/nodeids",
        "frontend/.vite/deps/_metadata.json",
    ]
    result = subprocess.run(
        ["git", "check-ignore", *ignored_paths],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_streamlit_is_legacy_profile_only() -> None:
    assert not (ROOT / "ui").exists()
    assert (ROOT / "legacy" / "ui" / "app.py").exists()
    assert (ROOT / "requirements-legacy.txt").exists()

    active_requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    legacy_requirements = (ROOT / "requirements-legacy.txt").read_text(encoding="utf-8")
    assert "streamlit" not in active_requirements
    assert "streamlit" in legacy_requirements

    pytest_ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "legacy" in pytest_ini
    assert 'not legacy' in pytest_ini


def test_key_api_routes_are_registered_from_router_modules_with_response_models() -> None:
    expected = [
        ("GET", "/cases/{case_id}", "backend.api.cases"),
        ("GET", "/history", "backend.api.history"),
        ("POST", "/agent/run", "backend.api.agent"),
        ("POST", "/cases/process", "backend.api.cases"),
        ("POST", "/cases/approve", "backend.api.cases"),
    ]
    for method, path, module_name in expected:
        route = _route(path, method)
        assert route.endpoint.__module__ == module_name
        assert route.response_model is not None


def test_legacy_build_draft_is_explicitly_deprecated_wrapper() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = draft.build_draft(
            case_id="CASE-1",
            category="szamlazas",
            output_mode="hitl",
            policy_map={"policy_items": []},
            actions=[],
        )

    assert result["generation_mode"] in {"template", "insufficient"}
    assert any(item.category is DeprecationWarning for item in caught)
