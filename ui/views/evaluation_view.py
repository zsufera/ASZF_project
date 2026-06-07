from __future__ import annotations

import streamlit as st

from ui import api_client


def render_evaluation_view() -> None:
    st.subheader("Evaluation")
    limit = st.slider("Minta-email limit", min_value=3, max_value=16, value=10)
    if st.button("Kiértékelés indítása", type="primary"):
        with st.spinner("Eval fut..."):
            try:
                result = api_client.run_eval(limit=limit)
            except api_client.ApiError as exc:
                st.error(str(exc))
                return
        col1, col2, col3 = st.columns(3)
        col1.metric("Osztályozás pontosság", f"{result.get('category_accuracy', 0):.0%}", help="Cél: magas")
        col2.metric("Retrieval support", f"{result.get('retrieval_support', 0):.0%}", help="Cél: ≥95%")
        col3.metric("Elemzett email", result.get("evaluated", 0))
        st.dataframe(result.get("results") or [], use_container_width=True)
