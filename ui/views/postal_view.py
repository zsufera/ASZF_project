from __future__ import annotations

import streamlit as st

from ui import api_client


def render_postal_view(username: str, default_output_mode: str) -> str | None:
    st.subheader("📮 Postai levél import")
    uploaded = st.file_uploader("PDF feltöltése", type=["pdf"])
    if not uploaded:
        st.info("Tölts fel egy PDF-et az OCR-előnézethez.")
        return None

    case_id = st.session_state.get("postal_case_id")
    if st.button("OCR futtatása"):
        try:
            created = api_client.create_case(channel="postal", input_text="Postai import előkészítés")
            case_id = created["case_id"]
            ocr = api_client.post_ocr(case_id, uploaded.name, uploaded.getvalue())
            st.session_state["postal_case_id"] = case_id
            st.session_state["postal_ocr"] = ocr
        except api_client.ApiError as exc:
            st.error(str(exc))
            return None

    ocr = st.session_state.get("postal_ocr")
    if not ocr:
        return None

    st.metric("OCR konfidencia", f"{ocr.get('ocr_confidence', 0):.2f}")
    edited = st.text_area(
        "OCR-eredmény (szerkeszthető)",
        value=ocr.get("ocr_text_masked", ""),
        height=240,
    )
    if ocr.get("low_conf_spans"):
        st.caption("Alacsony konfidenciájú részek jelölve az OCR szolgáltatásban.")

    if st.button("Feldolgozás (email-flow)", type="primary"):
        case_id = st.session_state.get("postal_case_id")
        if not case_id:
            st.warning("Futtasd előbb az OCR-t.")
            return None
        try:
            api_client.process_case(
                case_id=case_id,
                output_mode=default_output_mode,
                username=username,
                input_text_masked=edited,
            )
            st.success("Postai szöveg feldolgozva.")
            return case_id
        except api_client.ApiError as exc:
            st.error(str(exc))
    return case_id
