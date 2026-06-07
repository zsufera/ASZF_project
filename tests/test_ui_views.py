from __future__ import annotations

from unittest import mock

from streamlit.testing.v1 import AppTest


def test_app_renders_login_when_no_user():
    at = AppTest.from_file("ui/app.py").run()
    assert not at.exception
