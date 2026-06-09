from __future__ import annotations

from typing import Any

import streamlit as st

from legacy.ui import api_client, components
from legacy.ui.components import (
    case_badges_html,
    highlight_inbound,
    render_history_panel,
    render_source_panel,
    render_timeline_one,
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

    # ĂśgyfejlĂ©c One-kĂˇrtyĂˇban
    st.markdown(
        "<div class='one-casehdr'>"
        f"<span style='font-size:18px;font-weight:800'>Ăśgy #{case.get('case_id')}</span>"
        f"&nbsp;&nbsp;{case_badges_html(case)}"
        f"<span style='float:right;color:var(--one-grey)'>đź“§ {case.get('sender_email_masked', 'â€”')}"
        f" Â· âŹ± SLA: {case.get('sla_days_remaining', 'â€”')} nap</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    agent_state = case.get("agent_state") or {}
    retrieval = agent_state.get("retrieval") or {}
    policy_map = agent_state.get("policy_map") or {}
    timeline = agent_state.get("timeline") or []
    draft_versions = case.get("draft_versions") or []

    if not timeline:
        if st.button("Agent feldolgozĂˇs indĂ­tĂˇsa", type="primary"):
            with st.status("Agent fut...", expanded=True):
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
        with components.card("đź“š ForrĂˇsok"):
            show_plain = st.toggle("KĂ¶zĂ©rthetĹ‘ magyarĂˇzat", value=True)
            render_source_panel(policy_map, retrieval, show_plain)
        with components.card("đź•“ ElĹ‘zmĂ©nyek"):
            render_history_panel(case.get("sender_email_masked"))
        with components.card("đź‘Ą ĂśgyfĂ©ltĂ¶rzs-jelĂ¶ltek"):
            candidates = case.get("customer_candidates") or []
            if not candidates:
                st.info("Nincs jelĂ¶lt.")
            selected_customer = st.session_state.get(f"customer_{case_id}")
            for candidate in candidates:
                label = f"{candidate['customer_name']} ({candidate['customer_id']})"
                if candidate.get("link_url"):
                    st.markdown(f"[{label}]({candidate['link_url']})")
                else:
                    st.markdown(label)
                if st.button(
                    f"KivĂˇlaszt: {candidate['customer_id']}",
                    key=f"pick_{case_id}_{candidate['customer_id']}",
                ):
                    st.session_state[f"customer_{case_id}"] = candidate["customer_id"]
                    st.rerun()
            if selected_customer:
                st.caption(f"KivĂˇlasztott ĂĽgyfĂ©l: `{selected_customer}`")

    with center:
        with components.card("âś‰ď¸Ź BejĂ¶vĹ‘ ĂĽzenet"):
            chunks = retrieval.get("chunks") or []
            inbound_html = highlight_inbound(case.get("inbound_text_masked", ""), chunks)
            st.markdown(inbound_html, unsafe_allow_html=True)

        with components.card("đź“ť VĂˇlaszlevĂ©l (draft)"):
            latest_draft = draft_versions[0] if draft_versions else {}
            draft_from_agent = agent_state.get("draft") or {}
            subject_default = latest_draft.get("subject") or draft_from_agent.get("subject") or ""
            body_default = latest_draft.get("body_masked") or draft_from_agent.get("body_masked") or ""

            top = st.columns([1, 1])
            output_mode = top[0].radio(
                "Kimeneti mĂłd",
                options=["hitl", "automata"],
                format_func=lambda v: "Human-in-the-loop" if v == "hitl" else "Teljes AI-automata",
                horizontal=True,
                index=0 if default_output_mode == "hitl" else 1,
            )
            use_template = top[1].toggle("StrukturĂˇlt sablonblokkok", value=False)

            if use_template:
                subject_default = st.text_input("TĂˇrgy", value=subject_default, key=f"subject_{case_id}")
                st.text_area("MegszĂłlĂ­tĂˇs", value="Tisztelt ĂśgyfelĂĽnk!", key=f"greet_{case_id}")
                body_default = st.text_area("TĂ¶rzs", value=body_default, height=220, key=f"body_tpl_{case_id}")
                st.text_area("ZĂˇrĂˇs", value="ĂśdvĂ¶zlettel,\nĂśgyfĂ©lszolgĂˇlat", key=f"close_{case_id}")
            else:
                subject_default = st.text_input("TĂˇrgy", value=subject_default, key=f"subject_free_{case_id}")
                body_default = st.text_area("Draft tĂ¶rzs", value=body_default, height=280, key=f"body_free_{case_id}")

            version_labels = [f"v{v['version_no']}" for v in draft_versions]
            if version_labels:
                picked = st.selectbox("VerziĂłtĂ¶rtĂ©net", version_labels)
                picked_draft = next(v for v in draft_versions if f"v{v['version_no']}" == picked)
                st.caption(f"VerziĂł lĂ©trehozva: {picked_draft.get('created_at', '')}")

            col_save, col_approve = st.columns(2)
            with col_save:
                if st.button("đź’ľ Draft mentĂ©se", use_container_width=True):
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
                if st.button("âś“ JĂłvĂˇhagyom kikĂĽldĂ©sre", type="primary", use_container_width=True):
                    try:
                        approve = api_client.approve_draft(
                            case_id=case_id,
                            subject_masked=subject_default,
                            body_masked=body_default,
                            username=username,
                            role=role,
                            draft_version_id=latest_draft.get("id"),
                        )
                        st.success("Mock kĂĽldĂ©s megtĂ¶rtĂ©nt, ĂĽgy lezĂˇrva.")
                        with st.expander("Unmask elĹ‘nĂ©zet (RBAC)"):
                            st.text(approve.get("subject_unmasked", ""))
                            st.text(approve.get("body_unmasked", ""))
                        st.rerun()
                    except api_client.ApiError as exc:
                        st.error(str(exc))

            st.markdown("**ĂśI-visszajelzĂ©s**")
            fb1, fb2, fb3 = st.columns(3)
            with fb1:
                if st.button("đź‘Ť JĂł vĂˇlasz", use_container_width=True):
                    api_client.submit_feedback(case_id=case_id, rating="jo", username=username)
                    st.toast("VisszajelzĂ©s rĂ¶gzĂ­tve.")
            with fb2:
                if st.button("đź‘Ž Rossz vĂˇlasz", use_container_width=True):
                    api_client.submit_feedback(case_id=case_id, rating="rossz", username=username)
                    st.toast("VisszajelzĂ©s rĂ¶gzĂ­tve.")
            with fb3:
                if st.button("Rossz forrĂˇs", use_container_width=True):
                    api_client.submit_feedback(case_id=case_id, rating="rossz", wrong_source=True, username=username)
                    st.toast("Rossz forrĂˇs jelĂ¶lve.")

    with right:
        render_timeline_one(timeline, expanded=True)
        escalation = agent_state.get("escalation") or {}
        if escalation.get("required"):
            st.warning("EszkalĂˇciĂł szĂĽksĂ©ges: " + ", ".join(escalation.get("reasons", [])))
            st.button("âš  EszkalĂˇciĂł supervisorhoz", key=f"esc_{case_id}")

