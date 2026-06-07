from __future__ import annotations

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
