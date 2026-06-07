import json

from backend.auth import ensure_users_in_db, get_user_id, verify_login
from backend.case_service import (
    approve_draft,
    create_ad_hoc_case,
    get_case_detail,
    list_inbox,
    process_case,
    save_draft_version,
    seed_inbox_from_samples,
    submit_feedback,
)
from backend.db import init_db


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
                "dok_cim": "ONE ÁSZF",
                "oldalszam": 12,
                "cross_refs": [],
                "source_file": "one.pdf",
                "retrieval_source": "hybrid_local",
            }
        ],
        "retrieval_mode": "hybrid_local",
        "result_count": 1,
    }


def test_verify_login_demo_users() -> None:
    assert verify_login("ui_demo", "ui_demo") == {"username": "ui_demo", "role": "ui"}
    assert verify_login("supervisor_demo", "supervisor_demo") == {
        "username": "supervisor_demo",
        "role": "supervisor",
    }
    assert verify_login("ui_demo", "wrong") is None


def test_seed_inbox_and_list(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.auth.settings.sqlite_path", str(db_path))
    init_db()
    result = seed_inbox_from_samples()
    assert result["seeded"] >= 10
    items = list_inbox()
    assert len(items) >= 10
    assert items[0]["case_id"].startswith("CASE-")


def test_process_and_approve_flow(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)
    monkeypatch.setattr("agent.runner.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.auth.settings.sqlite_path", str(db_path))
    init_db()
    ensure_users_in_db()

    case_id = create_ad_hoc_case(
        channel="email",
        input_text="Szamlazasi kifogasom van, ugyfelszolgalat@one.hu",
        sender_email="teszt@example.invalid",
        service_provider="ONE",
    )
    processed = process_case(case_code=case_id, output_mode="hitl", actor_user_id=get_user_id("ui_demo"))
    assert processed["classification"]["category"] == "szamlazas"
    assert processed.get("timeline")

    detail = get_case_detail(case_id)
    assert detail is not None
    assert detail["status"] in {"folyamatban", "eszkalalva"}
    assert detail["draft_versions"]

    saved = save_draft_version(
        case_code=case_id,
        subject="Re: Szamlazas",
        body_masked="Tisztelt Ugyfelunk, vizsgaljuk.",
        output_mode="hitl",
        citations=["one-5-1"],
    )
    assert saved["version_no"] >= 1

    approved = approve_draft(
        case_code=case_id,
        draft_version_id=saved["draft_version_id"],
        actor_user_id=1,
        actor_role="ui",
    )
    assert approved["mock_sent"] is True
    assert approved["status"] == "lezarva"

    feedback = submit_feedback(case_code=case_id, rating="jo", actor_user_id=1)
    assert feedback["rating"] == "jo"


def test_get_case_detail_agent_state(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)
    monkeypatch.setattr("agent.runner.settings.sqlite_path", str(db_path))
    init_db()

    case_id = create_ad_hoc_case(channel="email", input_text="Szamlazasi kerdes.")
    process_case(case_code=case_id, output_mode="hitl")
    detail = get_case_detail(case_id)
    assert detail is not None
    agent_state = detail.get("agent_state") or {}
    assert agent_state.get("timeline")
    assert agent_state.get("retrieval")
