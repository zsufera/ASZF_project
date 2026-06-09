from __future__ import annotations

import streamlit as st

from legacy.ui import api_client, components
from legacy.ui.components import escalation_badge, priority_badge, sla_badge


def render_supervisor_view(role: str = "supervisor", username: str = "") -> None:
    st.subheader("Supervisor â€” eszkalĂˇlt ĂĽgyek")
    try:
        queue = api_client.supervisor_queue()
        stats = api_client.supervisor_stats()
    except api_client.ApiError as exc:
        st.error(str(exc))
        return

    grid = [
        ("Ă–sszes ĂĽgy", str(stats.get("total_cases", 0)), "ok"),
        ("EszkalĂˇlt", str(stats.get("escalated_cases", 0)), "warn" if stats.get("escalated_cases") else "ok"),
        ("LezĂˇrt", str(stats.get("closed_cases", 0)), "ok"),
        ("EszkalĂˇciĂłs arĂˇny", f"{stats.get('escalation_rate', 0):.0%}", "ok"),
    ]
    components.render_kpi_grid(grid, per_row=4)

    st.markdown("**ĂśgyintĂ©zĹ‘nkĂ©nti feldolgozĂˇs**")
    for row in stats.get("by_operator") or []:
        st.markdown(f"- {row['username']}: {row['processed']} feldolgozĂˇs")

    st.markdown("**EszkalĂˇlt sor**")
    items = queue.get("items") or []
    if not items:
        st.info("Nincs eszkalĂˇlt ĂĽgy.")
        return
    for item in items:
        st.markdown(
            f"- `{item['case_id']}` {priority_badge(item.get('priority'))} "
            f"{escalation_badge(True)} {sla_badge(item.get('sla_days_remaining'))} "
            f"Â· {item.get('subject', '')[:80]}"
        )

    st.markdown("---")
    st.subheader("Audit Ă©s megĹ‘rzĂ©s")
    case_for_audit = st.text_input("Ăśgy azonosĂ­tĂł audit nĂ©zethez")
    if case_for_audit and st.button("Audit rekord betĂ¶ltĂ©se"):
        try:
            record = api_client.get_audit_record(case_for_audit, role=role)
            completeness = api_client.get_audit_completeness(case_for_audit, role=role)
            st.json({"completeness": completeness, "iterations": record.get("iterations", [])[:3]})
        except api_client.ApiError as exc:
            st.error(str(exc))

    if st.button("MegĹ‘rzĂ©si purge (dry-run)"):
        try:
            result = api_client.governance_purge(dry_run=True, username=username, role=role)
            st.json(result)
        except api_client.ApiError as exc:
            st.error(str(exc))

