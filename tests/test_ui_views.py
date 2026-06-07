from __future__ import annotations

from unittest import mock

from streamlit.testing.v1 import AppTest


def test_app_renders_login_when_no_user():
    at = AppTest.from_file("ui/app.py").run()
    assert not at.exception


def _sample_case():
    return {
        "case_id": "1234",
        "category_label": "Számlázás",
        "priority": "surgos",
        "confidence": 0.82,
        "escalated": True,
        "channel_label": "email",
        "status_label": "Folyamatban",
        "sla_days_remaining": 12,
        "sender_email_masked": "[NEV_1]@masked",
        "inbound_text_masked": "Téves díjtételt találtam a számlán.",
        "customer_candidates": [],
        "draft_versions": [],
        "agent_state": {
            "retrieval": {"chunks": [{"chunk_id": "c1", "paragrafus": "12.3",
                                       "quote": "a díj módosítását 30 nappal előre"}]},
            "policy_map": {},
            "timeline": [{"step": "classify", "output": {"category": "szamlazas"}}],
            "draft": {"subject": "Válasz", "body_masked": "Tisztelt Ügyfelünk!",
                      "citations": []},
            "escalation": {"required": True, "reasons": ["ismétlődő panasz"]},
        },
    }


def test_case_view_renders_with_timeline():
    def script():
        from unittest import mock
        import ui.views.case_view as cv
        from tests.test_ui_views import _sample_case
        cv.api_client = mock.MagicMock()
        cv.api_client.ApiError = RuntimeError
        cv.api_client.get_case.return_value = _sample_case()
        cv.api_client.get_history.return_value = {"items": [], "is_repeated": False}
        cv.render_case_view("1234", "ui_demo", "hitl", role="ui")
    at = AppTest.from_function(script).run()
    assert not at.exception
