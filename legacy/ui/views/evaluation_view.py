from __future__ import annotations

import json

import streamlit as st

from legacy.ui import api_client, components


def render_evaluation_view() -> None:
    st.subheader("Evaluation harness")
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.slider("Minta limit", min_value=3, max_value=16, value=10)
    with col2:
        category = st.selectbox(
            "KategĂłria szĹ±rĹ‘",
            ["", "szamlazas", "dijemeles", "hibabejelentes_szolgaltataskieses", "egyeb"],
            format_func=lambda value: "Ă–sszes" if not value else value,
        )
    with col3:
        provider = st.selectbox(
            "SzolgĂˇltatĂł",
            ["", "ONE", "helyi_kabeles", "AH_Media", "Invitech"],
            format_func=lambda value: "Ă–sszes" if not value else value,
        )
    include_edge = st.checkbox("Edge / adversariĂˇlis esetek", value=True)

    if st.button("KiĂ©rtĂ©kelĂ©s indĂ­tĂˇsa", type="primary"):
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
        st.info("IndĂ­ts kiĂ©rtĂ©kelĂ©st a KPI-k megjelenĂ­tĂ©sĂ©hez.")
        return

    kpis = result.get("kpis", {})
    values = kpis.get("values", {})
    status = kpis.get("status", {})

    st.caption(f"Run: `{result.get('run_id')}` Â· ĂSZF: {result.get('aszf_version') or 'â€”'}")

    def _kpi_status(key: str) -> str:
        return {"green": "ok", "yellow": "warn", "red": "bad"}.get(status.get(key, ""), "ok")

    grid = [
        ("Faithfulness", f"{values.get('faithfulness', 0):.0%}", _kpi_status("faithfulness")),
        ("Citation support", f"{values.get('citation_support_rate', 0):.0%}", _kpi_status("citation_support_rate")),
        ("Judge score", f"{values.get('judge_score', 0):.2f}", _kpi_status("judge_score")),
        ("Coverage", f"{values.get('coverage', 0):.0%}", _kpi_status("coverage")),
        ("EszkalĂˇciĂł", f"{values.get('escalation_appropriateness', 0):.0%}", _kpi_status("escalation_appropriateness")),
        ("Retrieval support", f"{values.get('retrieval_support', 0):.0%}", _kpi_status("retrieval_support")),
        ("IdĹ‘ p95 (ms)", f"{values.get('time_to_answer_ms_p95', 0)}", _kpi_status("time_to_answer_ms")),
        ("Out-of-scope", f"{values.get('out_of_scope_answer_rate', 0):.0%}", _kpi_status("out_of_scope_answer_rate")),
    ]
    components.render_kpi_grid(grid, per_row=4)

    baseline_diff = result.get("baseline_diff", {})
    if baseline_diff.get("has_baseline"):
        st.markdown("**RegressziĂł (baseline diff)**")
        st.json(baseline_diff.get("diff", {}))
    else:
        st.caption("Nincs mentett baseline â€” a Supervisor mentheti az aktuĂˇlis futĂˇst.")

    if st.button("Baseline mentĂ©se (aktuĂˇlis futĂˇs)"):
        try:
            api_client.save_eval_baseline(result["run_id"])
            st.success("Baseline mentve.")
        except api_client.ApiError as exc:
            st.error(str(exc))

    st.markdown("**KĂ©rdĂ©s-szintĹ± eredmĂ©nyek**")
    rows = result.get("results") or []
    st.dataframe(rows, use_container_width=True)

    st.markdown("**Emberi spot-check (1â€“5)**")
    if rows:
        picked = st.selectbox("Email", [row["email_id"] for row in rows])
        human_score = st.slider("Emberi pontszĂˇm", 1, 5, 3)
        if st.button("Emberi score mentĂ©se"):
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

