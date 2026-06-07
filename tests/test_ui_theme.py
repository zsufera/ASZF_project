from __future__ import annotations

from ui import theme


def test_tokens_have_required_keys():
    required = {"turq", "turq_d", "turq_l", "black", "ink", "grey", "line", "canvas"}
    assert required.issubset(theme.TOKENS.keys())
    assert theme.TOKENS["turq"].startswith("#")


def test_theme_css_contains_primary_color():
    css = theme.theme_css()
    assert css.strip().startswith("<style>")
    assert css.strip().endswith("</style>")
    assert theme.TOKENS["turq"] in css


def test_badge_html_known_kinds():
    html = theme.badge_html("priority", "surgos")
    assert "one-badge" in html and "SÜRGŐS" in html
    assert theme.badge_html("category", "Számlázás").count("Számlázás") == 1
    # ismeretlen kind biztonságos fallback
    assert "one-badge" in theme.badge_html("unknown", "x")
