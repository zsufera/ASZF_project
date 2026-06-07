from __future__ import annotations

from typing import Any

import streamlit as st

from ui import api_client
from ui.components import (
    highlight_inbound,
    render_case_header,
    render_history_panel,
    render_source_panel,
    render_timeline,
)


def render_case_view(case_id: str, username: str, default_output_mode: str, role: str = "ui") -> None:
    try:
        case = api_client.get_case(case_id)
    except api_client.ApiError as exc:
        st.error(str(exc))
        return
    if case.get("error"):
        st.error(case["error"])
        return

    render_case_header(case)
    agent_state = case.get("agent_state") or {}
    retrieval = agent_state.get("retrieval") or {}
    policy_map = agent_state.get("policy_map") or {}
    timeline = agent_state.get("timeline") or []
    draft_versions = case.get("draft_versions") or []

    if not timeline:
        if st.button("Agent feldolgozás indítása", type="primary"):
            with st.spinner("Agent fut..."):
                try:
                    result = api_client.process_case(
                        case_id=case_id,
                        output_mode=default_output_mode,
                        username=username,
                        service_provider=case.get("service_provider"),
                    )
                    st.session_state["last_agent_result"] = result
                    st.rerun()
                except api_client.ApiError as exc:
                    st.error(str(exc))
        return

    left, center, right = st.columns([1, 2, 1])
    with left:
        st.subheader("Kontextus")
        show_plain = st.toggle("Közérthető magyarázat", value=True)
        st.markdown("**Források**")
        render_source_panel(policy_map, retrieval, show_plain)
        st.markdown("**Előzmények**")
        render_history_panel(case.get("sender_email_masked"))
        st.markdown("**Ügyféltörzs-jelöltek**")
        candidates = case.get("customer_candidates") or []
        if not candidates:
            st.info("Nincs jelölt.")
        selected_customer = st.session_state.get(f"customer_{case_id}")
        for candidate in candidates:
            label = f"{candidate['customer_name']} ({candidate['customer_id']})"
            if candidate.get("link_url"):
                st.markdown(f"[{label}]({candidate['link_url']})")
            else:
                st.markdown(label)
            if st.button(f"Kiválaszt: {candidate['customer_id']}", key=f"pick_{case_id}_{candidate['customer_id']}"):
                st.session_state[f"customer_{case_id}"] = candidate["customer_id"]
                st.rerun()
        if selected_customer:
            st.caption(f"Kiválasztott ügyfél: `{selected_customer}`")

    with center:
        st.subheader("Tartalom")
        chunks = retrieval.get("chunks") or []
        inbound_html = highlight_inbound(case.get("inbound_text_masked", ""), chunks)
        st.markdown("**Bejövő üzenet**")
        st.markdown(inbound_html, unsafe_allow_html=True)

        latest_draft = draft_versions[0] if draft_versions else {}
        draft_from_agent = agent_state.get("draft") or {}
        subject_default = latest_draft.get("subject") or draft_from_agent.get("subject") or ""
        body_default = latest_draft.get("body_masked") or draft_from_agent.get("body_masked") or ""
        output_mode = st.radio(
            "Kimeneti mód",
            options=["hitl", "automata"],
            format_func=lambda value: "Human-in-the-loop" if value == "hitl" else "Teljes AI-automata",
            horizontal=True,
            index=0 if default_output_mode == "hitl" else 1,
        )
        use_template = st.toggle("Strukturált sablonblokkok", value=False)
        if use_template:
            st.text_input("Tárgy", value=subject_default, key=f"subject_{case_id}")
            st.text_area("Megszólítás", value="Tisztelt Ügyfelünk!", key=f"greet_{case_id}")
            body_default = st.text_area("Törzs", value=body_default, height=220, key=f"body_tpl_{case_id}")
            st.text_area("Zárás", value="Üdvözlettel,\nÜgyfélszolgálat", key=f"close_{case_id}")
        else:
            subject_default = st.text_input("Tárgy", value=subject_default, key=f"subject_free_{case_id}")
            body_default = st.text_area("Draft törzs", value=body_default, height=280, key=f"body_free_{case_id}")

        version_labels = [f"v{v['version_no']}" for v in draft_versions]
        if version_labels:
            picked = st.selectbox("Verziótörténet", version_labels)
            picked_draft = next(v for v in draft_versions if f"v{v['version_no']}" == picked)
            st.caption(f"Verzió létrehozva: {picked_draft.get('created_at', '')}")

        col_save, col_approve = st.columns(2)
        with col_save:
            if st.button("Draft mentése"):
                try:
                    api_client.save_draft(
                        case_id=case_id,
                        subject=subject_default,
                        body_masked=body_default,
                        output_mode=output_mode,
                        citations=draft_from_agent.get("citations", []),
                        username=username,
                    )
                    st.success("Draft mentve.")
                    st.rerun()
                except api_client.ApiError as exc:
                    st.error(str(exc))
        with col_approve:
            if st.button("Jóváhagyom kiküldésre", type="primary"):
                try:
                    approve = api_client.approve_draft(
                        case_id=case_id,
                        subject_masked=subject_default,
                        body_masked=body_default,
                        username=username,
                        role=role,
                        draft_version_id=latest_draft.get("id"),
                    )
                    st.success("Mock küldés megtörtént, ügy lezárva.")
                    with st.expander("Unmask előnézet (RBAC)"):
                        st.text(approve.get("subject_unmasked", ""))
                        st.text(approve.get("body_unmasked", ""))
                    st.rerun()
                except api_client.ApiError as exc:
                    st.error(str(exc))

        st.markdown("**ÜI-visszajelzés**")
        fb1, fb2, fb3 = st.columns(3)
        with fb1:
            if st.button("👍 Jó válasz"):
                api_client.submit_feedback(case_id=case_id, rating="jo", username=username)
                st.toast("Visszajelzés rögzítve.")
        with fb2:
            if st.button("👎 Rossz válasz"):
                api_client.submit_feedback(case_id=case_id, rating="rossz", username=username)
                st.toast("Visszajelzés rögzítve.")
        with fb3:
            if st.button("Rossz forrás"):
                api_client.submit_feedback(case_id=case_id, rating="rossz", wrong_source=True, username=username)
                st.toast("Rossz forrás jelölve.")

    with right:
        st.subheader("Agent-idővonal")
        render_timeline(timeline)
        escalation = agent_state.get("escalation") or {}
        if escalation.get("required"):
            st.warning("Eszkaláció szükséges: " + ", ".join(escalation.get("reasons", [])))
