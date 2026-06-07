import json

from backend.case_service import create_ad_hoc_case
from integrations.mock_email_adapter import MockEmailAdapter
from integrations.sqlite_case_store import SQLiteCaseStore


def test_sqlite_case_store_create_and_get(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))

    from backend.db import init_db

    init_db(str(db_path))

    store = SQLiteCaseStore()
    case_id = store.create_case(
        {
            "channel": "email",
            "input_text": "Szamlazasi kifogas teszt",
            "sender_email": "teszt@example.invalid",
            "service_provider": "ONE",
        }
    )
    detail = store.get_case(case_id)
    assert detail is not None
    assert detail["case_id"] == case_id


def test_mock_email_adapter_sends(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("integrations.mock_email_adapter.settings.sqlite_path", str(db_path))

    from backend.db import init_db

    init_db(str(db_path))
    case_id = create_ad_hoc_case(channel="email", input_text="Teszt ugy")

    adapter = MockEmailAdapter()
    result = adapter.send_mock(case_id, "Tárgy", "Maszkolt szoveg", actor="ui_demo")
    assert result["mock_sent"] is True

    detail = SQLiteCaseStore().get_case(case_id)
    assert detail is not None
    assert detail["status"] == "lezarva"
