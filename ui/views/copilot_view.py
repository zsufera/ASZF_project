from __future__ import annotations

from typing import Iterator

import streamlit as st

from ui import api_client
from ui.theme import chip_html


def _stream_lines(text: str) -> Iterator[str]:
    """A teljes választ soronként yieldeli (st.write_stream-hez, streamelés szimuláció)."""
    for line in text.splitlines(keepends=True):
        yield line


def _sources_md(chunks: list[dict]) -> str:
    chips = [
        chip_html(f"§{c.get('paragrafus', '—')} ⤴")
        for c in chunks[:4]
    ]
    return " ".join(chips)


def render_copilot_view(channel: str, username: str, default_output_mode: str) -> str | None:
    title = "💬 Chat-copilot" if channel == "chat" else "📞 Telefon-copilot"
    st.subheader(title)
    provider = st.selectbox(
        "Szolgáltató", ["ONE", "helyi_kabeles", "AH_Media", "Invitech"], key=f"prov_{channel}"
    )

    hist_key = f"chat_hist_{channel}"
    st.session_state.setdefault(hist_key, [])
    for turn in st.session_state[hist_key]:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"], unsafe_allow_html=True)

    placeholder = (
        "Írj kérdést, vagy illeszd be a hívásátiratot…"
        if channel == "phone"
        else "Írj üzenetet…"
    )
    prompt = st.chat_input(placeholder)
    created_case_id: str | None = None

    if prompt:
        st.session_state[hist_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            created = api_client.create_case(
                channel=channel, input_text=prompt, service_provider=provider
            )
            created_case_id = created["case_id"]
            result = api_client.process_case(
                case_id=created_case_id,
                output_mode=default_output_mode,
                username=username,
                service_provider=provider,
            )
            body = result.get("draft", {}).get("body_masked", "")
            chunks = result.get("retrieval", {}).get("chunks", [])
            with st.chat_message("assistant"):
                st.markdown("**Javasolt beszédpontok:**")
                st.write_stream(_stream_lines(body))
                if chunks:
                    st.markdown("Források: " + _sources_md(chunks), unsafe_allow_html=True)
            answer = "**Javasolt beszédpontok:**\n\n" + body
            if chunks:
                answer += "\n\nForrások: " + _sources_md(chunks)
            st.session_state[hist_key].append({"role": "assistant", "content": answer})

            if st.button("↗ Ügy létrehozása ebből a beszélgetésből", key=f"mkcase_{channel}"):
                return created_case_id
        except api_client.ApiError as exc:
            st.error(str(exc))

    return None
