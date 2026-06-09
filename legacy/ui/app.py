from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os

import streamlit as st

from legacy.ui import api_client, components, theme
from legacy.ui.views.case_view import render_case_view
from legacy.ui.views.copilot_view import render_copilot_view
from legacy.ui.views.evaluation_view import render_evaluation_view
from legacy.ui.views.free_input_view import render_free_input_view
from legacy.ui.views.inbox_view import render_inbox_view
from legacy.ui.views.postal_view import render_postal_view
from legacy.ui.views.supervisor_view import render_supervisor_view


st.set_page_config(page_title="ĂSZF Q&A Agent", layout="wide", page_icon="đź“¨")


def _login_form() -> None:
    theme.inject_theme()
    st.markdown(
        "<div style='text-align:center;margin-top:40px'>"
        "<span class='one-logo' style='width:54px;height:54px;font-size:22px'>one</span>"
        "<h2 style='color:var(--one-ink)'>ĂSZF Copilot â€” BejelentkezĂ©s</h2></div>",
        unsafe_allow_html=True,
    )
    st.caption("POC demo: `ui_demo` / `ui_demo` vagy `supervisor_demo` / `supervisor_demo`")
    with st.form("login"):
        username = st.text_input("FelhasznĂˇlĂłnĂ©v")
        password = st.text_input("JelszĂł", type="password")
        submitted = st.form_submit_button("BelĂ©pĂ©s")
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


def _sidebar(role: str) -> tuple[str, str, str]:
    user = st.session_state["user"]
    st.sidebar.markdown(
        f"<div style='padding:6px 0'><b>{user.get('username')}</b> Â· {role}</div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("KijelentkezĂ©s", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.sidebar.markdown("---")

    menu = ["Inbox", "Ăšj ĂĽgy", "Copilot", "Evaluation"]
    if role == "supervisor":
        menu.append("Supervisor")
    page = components.icon_nav(menu)

    st.sidebar.markdown("---")
    provider = st.sidebar.radio(
        "Modell-profil",
        ["cloud", "onprem"],
        format_func=lambda v: "FelhĹ‘ (Azure EU)" if v == "cloud" else "On-prem (Ollama)",
    )
    os.environ["PROVIDER"] = provider
    default_output_mode = st.sidebar.radio(
        "Kimeneti mĂłd (alap)",
        ["hitl", "automata"],
        format_func=lambda v: "Human-in-the-loop" if v == "hitl" else "Teljes AI-automata",
    )
    if st.sidebar.button("ĂšjraindexelĂ©s", help="Manifest + parse + index + derive_params"):
        with st.sidebar.spinner("Reindex..."):
            try:
                result = api_client.run_reindex(force=False)
                st.sidebar.success(f"Index kĂ©sz: {result.get('indexed_chunks', 0)} chunk")
            except api_client.ApiError as exc:
                st.sidebar.error(str(exc))
    return page, default_output_mode, provider


def _aszf_version() -> str:
    try:
        return api_client.request_json("GET", "/health").get("aszf_version") or "â€”"
    except api_client.ApiError:
        st.warning("Backend offline â€” az adatok nem tĂ¶lthetĹ‘k.")
        return "â€”"


def main() -> None:
    if "user" not in st.session_state:
        _login_form()
        return

    theme.inject_theme()
    user = st.session_state["user"]
    role = user.get("role", "ui")
    username = user.get("username", "")
    page, default_output_mode, provider = _sidebar(role)

    components.top_header(username, role, _aszf_version(), provider)

    st.session_state.setdefault("active_case_id", None)
    st.session_state.setdefault("view_mode", "list")

    # Teljes szĂ©lessĂ©gĹ± ĂĽgy-munkaĂˇllomĂˇs mĂłd
    if st.session_state["view_mode"] == "case" and st.session_state["active_case_id"]:
        if st.button("â† Vissza", key="back_to_list"):
            st.session_state["view_mode"] = "list"
            st.rerun()
        render_case_view(
            st.session_state["active_case_id"], username, default_output_mode, role=role
        )
        return

    # Lista mĂłd
    if page == "Inbox":
        case_id = render_inbox_view()
    elif page == "Ăšj ĂĽgy":
        case_id = render_free_input_view()
    elif page == "Copilot":
        tab_chat, tab_phone, tab_postal = st.tabs(
            ["đź’¬ Chat-copilot", "đź“ž Telefon-copilot", "đź“® Postai levĂ©l"]
        )
        with tab_chat:
            chat_case = render_copilot_view("chat", username, default_output_mode)
        with tab_phone:
            phone_case = render_copilot_view("phone", username, default_output_mode)
        with tab_postal:
            postal_case = render_postal_view(username, default_output_mode)
        case_id = chat_case or phone_case or postal_case
    elif page == "Evaluation":
        render_evaluation_view()
        case_id = None
    elif page == "Supervisor":
        render_supervisor_view(role=role, username=username)
        case_id = None
    else:
        case_id = None

    if case_id:
        st.session_state["active_case_id"] = case_id
        st.session_state["view_mode"] = "case"
        st.rerun()


if __name__ == "__main__":
    main()

