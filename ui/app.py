from __future__ import annotations

import sys
from pathlib import Path

# Streamlit a script mappáját teszi sys.path elejére; a `ui` csomag a projektgyökérből importálható.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os

import streamlit as st

from ui import api_client
from ui.views.case_view import render_case_view
from ui.views.copilot_view import render_copilot_view
from ui.views.evaluation_view import render_evaluation_view
from ui.views.free_input_view import render_free_input_view
from ui.views.inbox_view import render_inbox_view
from ui.views.postal_view import render_postal_view
from ui.views.supervisor_view import render_supervisor_view


st.set_page_config(page_title="ÁSZF Q&A Agent", layout="wide", page_icon="📨")


def _login_form() -> None:
    st.title("ÁSZF Q&A Agent — Bejelentkezés")
    st.caption("POC demo: `ui_demo` / `ui_demo` vagy `supervisor_demo` / `supervisor_demo`")
    with st.form("login"):
        username = st.text_input("Felhasználónév")
        password = st.text_input("Jelszó", type="password")
        submitted = st.form_submit_button("Belépés")
    if submitted:
        try:
            result = api_client.login(username, password)
        except api_client.ApiError as exc:
            st.error(str(exc))
            return
        if result.get("error"):
            st.error(result["error"])
            return
        st.session_state["user"] = result
        st.rerun()


def _sidebar() -> tuple[str, str]:
    user = st.session_state["user"]
    role = user.get("role", "ui")
    st.sidebar.markdown(f"**{user.get('username')}** · {role}")
    if st.sidebar.button("Kijelentkezés"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")
    provider = st.sidebar.radio("Modell-profil", ["cloud", "onprem"], format_func=lambda v: "Felhő (Azure EU)" if v == "cloud" else "On-prem (Ollama)")
    os.environ["PROVIDER"] = provider

    try:
        health = api_client.request_json("GET", "/health")
        st.sidebar.caption(f"ÁSZF: {health.get('aszf_version') or '—'}")
    except api_client.ApiError:
        st.sidebar.warning("Backend offline")

    if st.sidebar.button("Újraindexelés", help="Manifest + parse + index + derive_params"):
        with st.sidebar.spinner("Reindex..."):
            try:
                result = api_client.run_reindex(force=False)
                st.sidebar.success(f"Index kész: {result.get('indexed_chunks', 0)} chunk")
            except api_client.ApiError as exc:
                st.sidebar.error(str(exc))

    default_output_mode = st.sidebar.radio(
        "Kimeneti mód (alap)",
        ["hitl", "automata"],
        format_func=lambda v: "Human-in-the-loop" if v == "hitl" else "Teljes AI-automata",
    )

    menu = ["Inbox", "Szabad bevitel", "Csatornák", "Evaluation"]
    if role == "supervisor":
        menu.append("Supervisor")
    page = st.sidebar.radio("Nézet", menu)
    return page, default_output_mode


def main() -> None:
    if "user" not in st.session_state:
        _login_form()
        return

    page, default_output_mode = _sidebar()
    user = st.session_state["user"]
    username = user.get("username", "")

    if "active_case_id" not in st.session_state:
        st.session_state["active_case_id"] = None

    st.title("ÁSZF Q&A Agent — Ügyintézői copilot")

    if page == "Inbox":
        case_id = render_inbox_view()
        if case_id:
            st.session_state["active_case_id"] = case_id
            render_case_view(case_id, username, default_output_mode, role=user.get("role", "ui"))
    elif page == "Szabad bevitel":
        case_id = render_free_input_view()
        if case_id:
            st.session_state["active_case_id"] = case_id
            render_case_view(case_id, username, default_output_mode, role=user.get("role", "ui"))
    elif page == "Csatornák":
        tab_email, tab_chat, tab_phone, tab_postal = st.tabs(["Email", "Chat-copilot", "Telefon-copilot", "Postai levél"])
        with tab_email:
            case_id = render_free_input_view(channel="email")
        with tab_chat:
            case_id = render_copilot_view("chat", username, default_output_mode)
        with tab_phone:
            case_id = render_copilot_view("phone", username, default_output_mode)
        with tab_postal:
            case_id = render_postal_view(username, default_output_mode)
        if case_id:
            st.session_state["active_case_id"] = case_id
            render_case_view(case_id, username, default_output_mode, role=user.get("role", "ui"))
    elif page == "Evaluation":
        render_evaluation_view()
    elif page == "Supervisor":
        render_supervisor_view(role=user.get("role", "supervisor"), username=username)

    active = st.session_state.get("active_case_id")
    if active and page not in {"Evaluation", "Supervisor"} and st.sidebar.checkbox("Aktív ügy panel", value=False):
        render_case_view(active, username, default_output_mode, role=user.get("role", "ui"))


if __name__ == "__main__":
    main()
