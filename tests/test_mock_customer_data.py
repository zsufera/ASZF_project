from backend.case_service import get_case_detail
from backend.db import init_db
from backend.history import get_history
from backend.main import app
from backend.services.inbox_service import seed_inbox_from_samples
from fastapi.testclient import TestClient
from integrations.customer_directory import MockCustomerDirectory
import sqlite3


def test_mock_customer_directory_returns_customer_profile() -> None:
    directory = MockCustomerDirectory()

    candidates = directory.lookup_by_email("kovacs.anna.poc@example.invalid")
    profile = directory.get_customer("CUST-MOCK-001")

    assert candidates[0]["customer_id"] == "CUST-MOCK-001"
    assert candidates[0]["link_url"] == "/customer/CUST-MOCK-001"
    assert profile is not None
    assert profile["customer_number"] == "48192037"
    assert profile["service_provider"] == "ONE"


def test_seeded_case_gets_mock_customer_candidate_and_history(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.services.inbox_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.history.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    init_db()

    seed_inbox_from_samples(force=True)

    detail = get_case_detail("CASE-email-001-szamlazas-one")
    assert detail is not None
    assert detail["customer_candidates"][0]["customer_id"] == "CUST-MOCK-001"
    assert detail["customer_candidates"][0]["link_url"] == "/customer/CUST-MOCK-001"

    history = get_history(detail["sender_email_masked"], sender_email_key=detail["sender_email_key"])

    assert any(item["case_id"] == "MOCK-HIST-KA-001" for item in history["items"])
    assert history["is_repeated"] is True


def test_non_force_seed_refreshes_existing_mock_customer_candidates(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.services.inbox_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    init_db()
    seed_inbox_from_samples(force=True)

    with sqlite3.connect(db_path) as conn:
        case_id = conn.execute(
            "SELECT id FROM cases WHERE case_code = 'CASE-email-001-szamlazas-one'"
        ).fetchone()[0]
        conn.execute("DELETE FROM customer_candidates WHERE case_id = ?", (case_id,))
        conn.execute(
            """
            INSERT INTO customer_candidates
            (case_id, source, customer_id, customer_name, link_url, selected)
            VALUES (?, 'mock', 'CUST-DEMO-001', 'Teszt Ugyfel', 'https://example.local/customer/CUST-DEMO-001', 0)
            """,
            (case_id,),
        )
        conn.commit()

    seed_inbox_from_samples(force=False)

    detail = get_case_detail("CASE-email-001-szamlazas-one")
    assert detail is not None
    assert detail["customer_candidates"][0]["customer_id"] == "CUST-MOCK-001"


def test_customer_detail_endpoint_returns_mock_profile() -> None:
    with TestClient(app) as client:
        response = client.get("/customers/CUST-MOCK-001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "CUST-MOCK-001"
    assert payload["customer_number"] == "48192037"
