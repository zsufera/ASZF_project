from __future__ import annotations

import streamlit as st

from ui import api_client


def render_copilot_view(channel: str, username: str, default_output_mode: str) -> str | None:
    title = "Chat-copilot" if channel == "chat" else "Telefon-copilot"
    st.subheader(title)
    transcript = st.text_area("ÜI kérdése / beillesztett átirat", height=160)
    provider = st.selectbox("Szolgáltató", ["ONE", "helyi_kabeles", "AH_Media", "Invitech"])
    if st.button("Küldés", type="primary"):
        if not transcript.strip():
            st.warning("Adj meg szöveget.")
            return None
        try:
            created = api_client.create_case(
                channel=channel,
                input_text=transcript,
                service_provider=provider,
            )
            case_id = created["case_id"]
            result = api_client.process_case(
                case_id=case_id,
                output_mode=default_output_mode,
                username=username,
                service_provider=provider,
            )
            st.markdown("**Agent válasz (beszédpontok)**")
            st.text(result.get("draft", {}).get("body_masked", ""))
            with st.expander("Források"):
                for chunk in result.get("retrieval", {}).get("chunks", []):
                    st.markdown(f"- `{chunk.get('chunk_id')}` §{chunk.get('paragrafus', '—')}: {chunk.get('quote', '')[:160]}")
            return case_id
        except api_client.ApiError as exc:
            st.error(str(exc))
    return None
