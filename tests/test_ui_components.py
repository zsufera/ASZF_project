from __future__ import annotations

from streamlit.testing.v1 import AppTest

from ui import components


def test_case_badges_html_includes_category_and_priority():
    case = {
        "category_label": "Számlázás",
        "priority": "surgos",
        "confidence": 0.82,
        "escalated": True,
        "channel_label": "email",
    }
    html = components.case_badges_html(case)
    assert "Számlázás" in html
    assert "SÜRGŐS" in html
    assert "one-badge" in html
    assert "0.82" in html


def test_case_badges_html_no_escalation_when_false():
    html = components.case_badges_html({"priority": "normal", "escalated": False})
    assert "ESZKAL" not in html.upper()


def test_top_header_renders_without_error():
    def script():
        from ui import components, theme
        theme.inject_theme()
        components.top_header(
            username="ui_demo", role="ui", aszf_version="v3.2", provider="cloud"
        )
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_icon_nav_returns_first_when_no_selection():
    def script():
        import streamlit as st
        from ui import components
        choice = components.icon_nav(["Inbox", "Új ügy", "Copilot"])
        st.session_state["_choice"] = choice
    at = AppTest.from_function(script).run()
    assert not at.exception
    assert at.session_state["_choice"] == "Inbox"


def test_render_timeline_collapsible_default_open_no_error():
    def script():
        from ui import components
        timeline = [
            {"step": "classify", "output": {"category": "szamlazas"}},
            {"step": "escalation", "output": {"required": True, "reasons": ["ismétlődő"]}},
        ]
        components.render_timeline_one(timeline, expanded=True)
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_render_kpi_grid_no_error():
    def script():
        from ui import components, theme
        theme.inject_theme()
        components.render_kpi_grid([
            ("Citation rate", "0.94", "ok"),
            ("Hallucináció", "0.02", "ok"),
            ("Coverage", "0.71", "warn"),
        ])
    at = AppTest.from_function(script).run()
    assert not at.exception
