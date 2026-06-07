from __future__ import annotations

import streamlit as st

from ui import api_client
from ui.components import case_badges_html


def render_inbox_view() -> str | None:
    st.subheader("📥 Ügyintézői inbox")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        category = st.selectbox(
            "Kategória",
            ["", "szamlazas", "dijemeles", "hibabejelentes_szolgaltataskieses", "egyeb"],
            format_func=lambda value: "Összes" if not value else value,
        )
    with col2:
        priority = st.selectbox("Prioritás", ["", "surgos", "normal"], format_func=lambda v: "Összes" if not v else v)
    with col3:
        status = st.selectbox(
            "Státusz",
            ["", "uj", "folyamatban", "eszkalalva", "jovahagyasra_var", "lezarva"],
            format_func=lambda v: "Összes" if not v else v,
        )
    with col4:
        channel = st.selectbox("Csatorna", ["", "email", "chat", "phone", "postal"], format_func=lambda v: "Összes" if not v else v)
    with col5:
        sort_by = st.selectbox(
            "Rendezés",
            ["priority", "sla", "created_at"],
            format_func=lambda v: {"priority": "Prioritás", "sla": "SLA", "created_at": "Beérkezés"}[v],
        )

    search = st.text_input("🔍 Keresés (azonosító, feladó, tárgy)")

    try:
        payload = api_client.list_inbox(
            category=category or None,
            priority=priority or None,
            status=status or None,
            channel=channel or None,
            search=search or None,
            sort_by=sort_by,
        )
    except api_client.ApiError as exc:
        st.error(str(exc))
        return None

    items = payload.get("items") or []
    if not items:
        st.info("Nincs megjeleníthető üzenet.")
        return None

    for item in items:
        with st.container(border=True):
            cols = st.columns([5, 1])
            with cols[0]:
                st.markdown(case_badges_html(item), unsafe_allow_html=True)
                st.markdown(
                    f"**{item.get('subject', '')[:80]}** · ⏱ {item.get('sla_days_remaining', '—')} nap"
                )
            with cols[1]:
                if st.button("Megnyitás", key=f"open_{item['case_id']}", type="primary"):
                    return item["case_id"]
    return None
