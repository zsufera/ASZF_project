from __future__ import annotations

import streamlit as st

from legacy.ui import api_client


def render_free_input_view(channel: str = "email") -> str | None:
    st.subheader("âśŹď¸Ź Ăšj ĂĽgy / szabad bevitel")
    text = st.text_area("Email beillesztĂ©se vagy szabad szĂ¶veges kĂ©rdĂ©s", height=220)
    sender = st.text_input("FeladĂł email (opcionĂˇlis)")
    provider = st.selectbox("SzolgĂˇltatĂł", ["", "ONE", "helyi_kabeles", "AH_Media", "Invitech"])
    if st.button("FeldolgozĂˇs", type="primary"):
        if not text.strip():
            st.warning("Adj meg szĂ¶veget.")
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

