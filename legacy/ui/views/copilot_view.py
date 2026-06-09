from __future__ import annotations

from typing import Iterator

import streamlit as st

from legacy.ui import api_client
from legacy.ui.theme import chip_html


def _stream_lines(text: str) -> Iterator[str]:
    """A teljes vĂˇlaszt soronkĂ©nt yieldeli (st.write_stream-hez, streamelĂ©s szimulĂˇciĂł)."""
    for line in text.splitlines(keepends=True):
        yield line


def _sources_md(chunks: list[dict]) -> str:
    chips = [
        chip_html(f"Â§{c.get('paragrafus', 'â€”')} â¤´")
        for c in chunks[:4]
    ]
    return " ".join(chips)


def render_copilot_view(channel: str, username: str, default_output_mode: str) -> str | None:
    title = "đź’¬ Chat-copilot" if channel == "chat" else "đź“ž Telefon-copilot"
    st.subheader(title)
    provider = st.selectbox(
        "SzolgĂˇltatĂł", ["ONE", "helyi_kabeles", "AH_Media", "Invitech"], key=f"prov_{channel}"
    )

    hist_key = f"chat_hist_{channel}"
    case_key = f"chat_case_{channel}"
    st.session_state.setdefault(hist_key, [])
    for turn in st.session_state[hist_key]:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"], unsafe_allow_html=True)

    placeholder = (
        "ĂŤrj kĂ©rdĂ©st, vagy illeszd be a hĂ­vĂˇsĂˇtiratotâ€¦"
        if channel == "phone"
        else "ĂŤrj ĂĽzenetetâ€¦"
    )
    prompt = st.chat_input(placeholder)

    if prompt:
        st.session_state[hist_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            created = api_client.create_case(
                channel=channel, input_text=prompt, service_provider=provider
            )
            result = api_client.process_case(
                case_id=created["case_id"],
                output_mode=default_output_mode,
                username=username,
                service_provider=provider,
            )
            body = result.get("draft", {}).get("body_masked", "")
            chunks = result.get("retrieval", {}).get("chunks", [])
            with st.chat_message("assistant"):
                st.markdown("**Javasolt beszĂ©dpontok:**")
                st.write_stream(_stream_lines(body))
                if chunks:
                    st.markdown("ForrĂˇsok: " + _sources_md(chunks), unsafe_allow_html=True)
            answer = "**Javasolt beszĂ©dpontok:**\n\n" + body
            if chunks:
                answer += "\n\nForrĂˇsok: " + _sources_md(chunks)
            st.session_state[hist_key].append({"role": "assistant", "content": answer})
            st.session_state[case_key] = created["case_id"]
        except api_client.ApiError as exc:
            st.error(str(exc))

    # Az "Ăśgy lĂ©trehozĂˇsa" gomb a prompt-blokkon KĂŤVĂśL, hogy a kattintĂˇs utĂˇni
    # rerunban is megjelenjen Ă©s visszaadja a case_id-t.
    if st.session_state.get(case_key):
        if st.button("â†— Ăśgy lĂ©trehozĂˇsa ebbĹ‘l a beszĂ©lgetĂ©sbĹ‘l", key=f"mkcase_{channel}"):
            return st.session_state.pop(case_key)

    return None

