"""Operational KPI aggregation from existing audit/case data."""
import json
import sqlite3

from backend.db import init_db
from backend.services.metrics_service import get_operational_metrics
from config.settings import settings


def _setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setattr(settings, "sqlite_path", str(db_path))
    init_db()
    return db_path


def _insert_case(conn, case_code, status="lezarva", escalated=0):
    conn.execute(
        """
        INSERT INTO cases (case_code, channel, status, priority, escalated, created_at, updated_at)
        VALUES (?, 'email', ?, 'normal', ?, '2026-06-10T08:00:00+00:00', '2026-06-10T08:00:00+00:00')
        """,
        (case_code, status, escalated),
    )
    return conn.execute("SELECT id FROM cases WHERE case_code = ?", (case_code,)).fetchone()[0]


def _insert_draft(conn, case_id, version_no, body):
    conn.execute(
        """
        INSERT INTO draft_versions (case_id, version_no, subject, body_masked, output_mode, disclaimer_applied, citations)
        VALUES (?, ?, 'Targy', ?, 'hitl', 0, '[]')
        """,
        (case_id, version_no, body),
    )


def _insert_event(conn, case_id, event_type, created_at, payload="{}"):
    conn.execute(
        """
        INSERT INTO audit_events (case_id, event_type, payload, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (case_id, event_type, payload, created_at),
    )


def test_empty_db_returns_zero_metrics(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    metrics = get_operational_metrics()
    assert metrics["case_funnel"] == {
        "total_cases": 0,
        "processed_cases": 0,
        "closed_cases": 0,
        "adoption_rate": 0.0,
    }
    assert metrics["handling_time"]["sample_size"] == 0
    assert metrics["handling_time"]["avg_seconds"] is None
    assert metrics["draft_acceptance"]["sample_size"] == 0
    assert metrics["feedback"]["positive_rate"] is None


def test_handling_time_from_audit_events(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    with sqlite3.connect(settings.sqlite_path) as conn:
        case_id = _insert_case(conn, "CASE-T1")
        _insert_event(conn, case_id, "case_iteration", "2026-06-10T08:00:00+00:00")
        _insert_event(conn, case_id, "draft_approved_mock_send", "2026-06-10T08:02:00+00:00")
        conn.commit()
    metrics = get_operational_metrics()
    assert metrics["handling_time"]["avg_seconds"] == 120.0
    assert metrics["handling_time"]["median_seconds"] == 120.0
    assert metrics["handling_time"]["sample_size"] == 1


def test_draft_acceptance_bands(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    body = "Tisztelt Ugyfelunk! A szamlazasi kifogast kivizsgaljuk es 30 napon belul valaszolunk."
    with sqlite3.connect(settings.sqlite_path) as conn:
        c1 = _insert_case(conn, "CASE-A1")
        _insert_draft(conn, c1, 1, body)
        _insert_draft(conn, c1, 2, body)
        c2 = _insert_case(conn, "CASE-A2")
        _insert_draft(conn, c2, 1, body)
        _insert_draft(
            conn,
            c2,
            2,
            "Teljesen mas szoveg, az ugyintezo mindent ujrairt, semmi sem maradt az eredetibol.",
        )
        conn.commit()
    metrics = get_operational_metrics()
    assert metrics["draft_acceptance"]["unchanged"] == 1
    assert metrics["draft_acceptance"]["rewrite"] == 1
    assert metrics["draft_acceptance"]["light_edit"] == 0
    assert metrics["draft_acceptance"]["sample_size"] == 2


def test_adoption_rate(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    with sqlite3.connect(settings.sqlite_path) as conn:
        c1 = _insert_case(conn, "CASE-P1", status="folyamatban")
        _insert_draft(conn, c1, 1, "Draft szoveg")
        _insert_case(conn, "CASE-P2", status="uj")
        conn.commit()
    metrics = get_operational_metrics()
    assert metrics["case_funnel"]["total_cases"] == 2
    assert metrics["case_funnel"]["processed_cases"] == 1
    assert metrics["case_funnel"]["adoption_rate"] == 0.5


def test_feedback_aggregation_with_reason_and_category(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    with sqlite3.connect(settings.sqlite_path) as conn:
        c1 = _insert_case(conn, "CASE-F1", escalated=1)
        _insert_event(
            conn,
            c1,
            "case_iteration",
            "2026-06-10T08:00:00+00:00",
            json.dumps({"category": "szamlazas"}),
        )
        _insert_event(
            conn,
            c1,
            "ui_feedback",
            "2026-06-10T08:05:00+00:00",
            json.dumps({"rating": "jo", "wrong_source": False}),
        )
        _insert_event(
            conn,
            c1,
            "ui_feedback",
            "2026-06-10T08:06:00+00:00",
            json.dumps({"rating": "rossz", "wrong_source": True, "reason": "rossz_forras"}),
        )
        conn.commit()
    metrics = get_operational_metrics()
    fb = metrics["feedback"]
    assert fb["good"] == 1
    assert fb["bad"] == 1
    assert fb["wrong_source"] == 1
    assert fb["positive_rate"] == 0.5
    assert fb["by_reason"] == {"rossz_forras": 1}
    assert fb["by_category"] == [{"category": "szamlazas", "good": 1, "bad": 1}]
    assert metrics["escalation"]["escalated_cases"] == 1


def test_metrics_route_registered() -> None:
    from fastapi.routing import APIRoute

    from backend.main import app

    assert any(
        isinstance(route, APIRoute) and route.path == "/metrics/operational"
        for route in app.routes
    )


def test_submit_feedback_records_reason(tmp_path, monkeypatch) -> None:
    from backend.case_service import submit_feedback

    _setup_db(tmp_path, monkeypatch)
    with sqlite3.connect(settings.sqlite_path) as conn:
        _insert_case(conn, "CASE-FB1")
        conn.commit()
    submit_feedback("CASE-FB1", rating="rossz", wrong_source=False, reason="hianyos")
    metrics = get_operational_metrics()
    assert metrics["feedback"]["bad"] == 1
    assert metrics["feedback"]["by_reason"] == {"hianyos": 1}
