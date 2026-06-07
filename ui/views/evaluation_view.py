from __future__ import annotations

import json

import streamlit as st

from ui import api_client


def _status_emoji(status: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status, "⚪")


def render_evaluation_view() -> None:
    st.subheader("Evaluation harness")
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.slider("Minta limit", min_value=3, max_value=16, value=10)
    with col2:
        category = st.selectbox(
            "Kategória szűrő",
            ["", "szamlazas", "dijemeles", "hibabejelentes_szolgaltataskieses", "egyeb"],
            format_func=lambda value: "Összes" if not value else value,
        )
    with col3:
        provider = st.selectbox(
            "Szolgáltató",
            ["", "ONE", "helyi_kabeles", "AH_Media", "Invitech"],
            format_func=lambda value: "Összes" if not value else value,
        )
    include_edge = st.checkbox("Edge / adversariális esetek", value=True)

    if st.button("Kiértékelés indítása", type="primary"):
        with st.spinner("Eval fut..."):
            try:
                result = api_client.run_eval(
                    limit=limit,
                    category=category or None,
                    service_provider=provider or None,
                    include_edge=include_edge,
                )
            except api_client.ApiError as exc:
                st.error(str(exc))
                return
        st.session_state["last_eval"] = result

    result = st.session_state.get("last_eval")
    if not result:
        st.info("Indíts kiértékelést a KPI-k megjelenítéséhez.")
        return

    kpis = result.get("kpis", {})
    values = kpis.get("values", {})
    status = kpis.get("status", {})
    targets = kpis.get("targets", {})

    st.caption(f"Run: `{result.get('run_id')}` · ÁSZF: {result.get('aszf_version') or '—'}")

    metric_cols = st.columns(4)
    cards = [
        ("faithfulness", "Faithfulness", "{:.0%}"),
        ("citation_support_rate", "Citation support", "{:.0%}"),
        ("judge_score", "Judge score", "{:.2f}"),
        ("coverage", "Coverage", "{:.0%}"),
    ]
    for idx, (key, label, fmt) in enumerate(cards):
        value = values.get(key, 0)
        display = fmt.format(value) if "%" in fmt else fmt.format(value)
        metric_cols[idx].metric(
            label,
            display,
            help=f"Cél: {targets.get(key, '—')} {_status_emoji(status.get(key, ''))}",
        )

    more_cols = st.columns(4)
    more_cards = [
        ("escalation_appropriateness", "Eszkaláció", "{:.0%}"),
        ("retrieval_support", "Retrieval support", "{:.0%}"),
        ("time_to_answer_ms", "Idő p95 (ms)", "{}"),
        ("out_of_scope_answer_rate", "Out-of-scope", "{:.0%}"),
    ]
    for idx, (key, label, fmt) in enumerate(more_cards):
        value = values.get(key if key != "time_to_answer_ms" else "time_to_answer_ms_p95", 0)
        if key == "time_to_answer_ms":
            value = values.get("time_to_answer_ms_p95", 0)
        display = fmt.format(value)
        more_cols[idx].metric(label, display, help=f"Cél: {targets.get(key, '—')}")

    baseline_diff = result.get("baseline_diff", {})
    if baseline_diff.get("has_baseline"):
        st.markdown("**Regresszió (baseline diff)**")
        st.json(baseline_diff.get("diff", {}))
    else:
        st.caption("Nincs mentett baseline — a Supervisor mentheti az aktuális futást.")

    if st.button("Baseline mentése (aktuális futás)"):
        try:
            api_client.save_eval_baseline(result["run_id"])
            st.success("Baseline mentve.")
        except api_client.ApiError as exc:
            st.error(str(exc))

    st.markdown("**Kérdés-szintű eredmények**")
    rows = result.get("results") or []
    st.dataframe(rows, use_container_width=True)

    st.markdown("**Emberi spot-check (1–5)**")
    if rows:
        picked = st.selectbox("Email", [row["email_id"] for row in rows])
        human_score = st.slider("Emberi pontszám", 1, 5, 3)
        if st.button("Emberi score mentése"):
            try:
                api_client.save_human_score(result["run_id"], picked, human_score)
                st.toast("Mentve.")
            except api_client.ApiError as exc:
                st.error(str(exc))

    st.download_button(
        "Riport export (JSON)",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name=f"eval_{result.get('run_id', 'report')}.json",
        mime="application/json",
    )
