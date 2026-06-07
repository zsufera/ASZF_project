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


def test_inbox_view_renders_items():
    def script():
        from unittest import mock
        import ui.views.inbox_view as iv
        iv.api_client = mock.MagicMock()
        iv.api_client.ApiError = RuntimeError
        iv.api_client.list_inbox.return_value = {"items": [
            {"case_id": "1", "category_label": "Számlázás", "priority": "surgos",
             "status_label": "Új", "channel_label": "email", "subject": "Téves számla",
             "sla_days_remaining": 2, "escalated": False, "confidence": 0.8},
        ]}
        iv.render_inbox_view()
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_copilot_view_renders_empty_chat():
    def script():
        from unittest import mock
        import ui.views.copilot_view as cv
        cv.api_client = mock.MagicMock()
        cv.api_client.ApiError = RuntimeError
        cv.render_copilot_view("chat", "ui_demo", "hitl")
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_copilot_stream_lines_yields_talking_points():
    import ui.views.copilot_view as cv
    out = "".join(cv._stream_lines("• pont 1\n• pont 2"))
    assert "pont 1" in out and "pont 2" in out


def test_copilot_create_case_button_returns_case_id():
    def script():
        from unittest import mock
        import streamlit as st
        import ui.views.copilot_view as cv
        cv.api_client = mock.MagicMock()
        cv.api_client.ApiError = RuntimeError
        st.session_state.setdefault("chat_case_chat", "C9")
        result = cv.render_copilot_view("chat", "ui_demo", "hitl")
        st.session_state["_result"] = result
    at = AppTest.from_function(script).run()
    assert not at.exception
    assert any("Ügy létrehozása" in b.label for b in at.button)
    at.button(key="mkcase_chat").click().run()
    assert at.session_state["_result"] == "C9"


def test_free_input_view_renders():
    def script():
        from unittest import mock
        import ui.views.free_input_view as fv
        fv.api_client = mock.MagicMock()
        fv.api_client.ApiError = RuntimeError
        fv.render_free_input_view()
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_postal_view_renders():
    def script():
        from unittest import mock
        import ui.views.postal_view as pv
        pv.api_client = mock.MagicMock()
        pv.api_client.ApiError = RuntimeError
        pv.render_postal_view("ui_demo", "hitl")
    at = AppTest.from_function(script).run()
    assert not at.exception
