from __future__ import annotations

import streamlit as st

from ui import api_client, components
from ui.components import escalation_badge, priority_badge, sla_badge


def render_supervisor_view(role: str = "supervisor", username: str = "") -> None:
    st.subheader("Supervisor — eszkalált ügyek")
    try:
        queue = api_client.supervisor_queue()
        stats = api_client.supervisor_stats()
    except api_client.ApiError as exc:
        st.error(str(exc))
        return

    grid = [
        ("Összes ügy", str(stats.get("total_cases", 0)), "ok"),
        ("Eszkalált", str(stats.get("escalated_cases", 0)), "warn" if stats.get("escalated_cases") else "ok"),
        ("Lezárt", str(stats.get("closed_cases", 0)), "ok"),
        ("Eszkalációs arány", f"{stats.get('escalation_rate', 0):.0%}", "ok"),
    ]
    components.render_kpi_grid(grid, per_row=4)

    st.markdown("**Ügyintézőnkénti feldolgozás**")
    for row in stats.get("by_operator") or []:
        st.markdown(f"- {row['username']}: {row['processed']} feldolgozás")

    st.markdown("**Eszkalált sor**")
    items = queue.get("items") or []
    if not items:
        st.info("Nincs eszkalált ügy.")
        return
    for item in items:
        st.markdown(
            f"- `{item['case_id']}` {priority_badge(item.get('priority'))} "
            f"{escalation_badge(True)} {sla_badge(item.get('sla_days_remaining'))} "
            f"· {item.get('subject', '')[:80]}"
        )

    st.markdown("---")
    st.subheader("Audit és megőrzés")
    case_for_audit = st.text_input("Ügy azonosító audit nézethez")
    if case_for_audit and st.button("Audit rekord betöltése"):
        try:
            record = api_client.get_audit_record(case_for_audit, role=role)
            completeness = api_client.get_audit_completeness(case_for_audit, role=role)
            st.json({"completeness": completeness, "iterations": record.get("iterations", [])[:3]})
        except api_client.ApiError as exc:
            st.error(str(exc))

    if st.button("Megőrzési purge (dry-run)"):
        try:
            result = api_client.governance_purge(dry_run=True, username=username, role=role)
            st.json(result)
        except api_client.ApiError as exc:
            st.error(str(exc))
