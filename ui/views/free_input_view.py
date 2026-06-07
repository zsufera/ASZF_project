from __future__ import annotations

import streamlit as st

from ui import api_client


def render_free_input_view(channel: str = "email") -> str | None:
    st.subheader("Szabad bevitel")
    text = st.text_area("Email beillesztése vagy szabad szöveges kérdés", height=220)
    sender = st.text_input("Feladó email (opcionális)")
    provider = st.selectbox("Szolgáltató", ["", "ONE", "helyi_kabeles", "AH_Media", "Invitech"])
    if st.button("Feldolgozás", type="primary"):
        if not text.strip():
            st.warning("Adj meg szöveget.")
            return None
        try:
            created = api_client.create_case(
                channel=channel,
                input_text=text,
                sender_email=sender or None,
                service_provider=provider or None,
            )
            return created.get("case_id")
        except api_client.ApiError as exc:
            st.error(str(exc))
    return None
