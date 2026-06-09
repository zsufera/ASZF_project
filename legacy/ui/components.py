from __future__ import annotations

from typing import Any

import streamlit as st

from legacy.ui import theme


def priority_badge(priority: str | None) -> str:
    if priority == "surgos":
        return "đź”´ SĂśRGĹS"
    return "âšŞ normĂˇl"


def escalation_badge(escalated: bool) -> str:
    return "âš  ESZKALĂLT" if escalated else ""


def confidence_badge(confidence: float | None, threshold: float = 0.75) -> str:
    if confidence is None:
        return "Konfidencia: â€”"
    color = "đźź˘" if confidence >= threshold else "đźźˇ"
    return f"{color} Konf: {confidence:.2f}"


def sla_badge(days_remaining: int | None) -> str:
    if days_remaining is None:
        return "SLA: â€”"
    if days_remaining <= 3:
        return f"đź”´ SLA: {days_remaining} nap"
    if days_remaining <= 7:
        return f"đźźˇ SLA: {days_remaining} nap"
    return f"đźź˘ SLA: {days_remaining} nap"


def render_case_header(case: dict[str, Any]) -> None:
    cols = st.columns([2, 1, 1, 1, 1])
    cols[0].markdown(f"### Ăśgy `{case.get('case_id')}`")
    cols[1].markdown(f"**{case.get('category_label', 'â€”')}**")
    cols[2].markdown(priority_badge(case.get("priority")))
    cols[3].markdown(confidence_badge(case.get("confidence")))
    cols[4].markdown(sla_badge(case.get("sla_days_remaining")))
    badges = [
        case.get("status_label"),
        case.get("channel_label"),
        escalation_badge(case.get("escalated")),
    ]
    st.caption(" | ".join(part for part in badges if part))


def render_source_panel(policy_map: dict[str, Any], retrieval: dict[str, Any], show_plain: bool) -> None:
    items = policy_map.get("policy_items") or retrieval.get("chunks") or []
    if not items:
        st.info("Nincs forrĂˇs a megjelenĂ­tĂ©shez.")
        return
    for item in items:
        chunk_id = item.get("chunk_id", "â€”")
        dok_tipus = item.get("dok_tipus", "ĂSZF")
        paragrafus = item.get("paragrafus") or item.get("paragrafus_szam") or "â€”"
        quote = item.get("idezet") or item.get("quote") or ""
        with st.expander(f"Â§{paragrafus} Â· {dok_tipus} Â· `{chunk_id}`", expanded=False):
            st.markdown(f"> {quote}")
            if show_plain and item.get("kozertheto_magyarazat"):
                st.markdown(f"**KĂ¶zĂ©rthetĹ‘ magyarĂˇzat:** {item['kozertheto_magyarazat']}")
            elif show_plain:
                st.caption("KĂ¶zĂ©rthetĹ‘ magyarĂˇzat: a POC determinisztikus policy-map alapjĂˇn.")


def render_timeline(timeline: list[dict[str, Any]]) -> None:
    if not timeline:
        st.info("Az agent mĂ©g nem futott le.")
        return
    for entry in timeline:
        step = entry.get("step", "â€”")
        output = entry.get("output", {})
        warning = ""
        if step == "escalation" and output.get("required"):
            warning = " âš "
        elif step == "verify" and output.get("ungrounded_count", 0) > 0:
            warning = " âš "
        with st.expander(f"{step}{warning}", expanded=step in {"escalation", "verify"}):
            st.json(output)


def render_history_panel(address: str | None) -> None:
    if not address:
        st.info("Nincs feladĂł-cĂ­m az elĹ‘zmĂ©nyekhez.")
        return
    from legacy.ui import api_client

    try:
        history = api_client.get_history(address)
    except api_client.ApiError as exc:
        st.warning(str(exc))
        return
    if history.get("is_repeated"):
        st.warning("IsmĂ©tlĹ‘dĹ‘ panasz jelzĂ©s az elĹ‘zmĂ©nyek alapjĂˇn.")
    items = history.get("items") or []
    if not items:
        st.info("Nincs korĂˇbbi ĂĽzenet ehhez a cĂ­mhez.")
        return
    for item in items:
        st.markdown(
            f"- **{item.get('date', '')[:10]}** Â· {item.get('subject', '')[:80]} "
            f"Â· {item.get('category', 'â€”')} Â· `{item.get('status', '')}`"
        )


def highlight_inbound(text: str, chunks: list[dict[str, Any]]) -> str:
    highlighted = text
    for chunk in chunks[:3]:
        quote = (chunk.get("quote") or chunk.get("idezet") or "").strip()
        if len(quote) < 12:
            continue
        snippet = quote[:40]
        if snippet and snippet in highlighted:
            highlighted = highlighted.replace(
                snippet,
                f"<mark title='{chunk.get('chunk_id', '')}'>{snippet}</mark>",
                1,
            )
    return highlighted


def case_badges_html(case: dict[str, Any]) -> str:
    """SzĂ­nkĂłdolt One badge-sor egy ĂĽgyhĂ¶z/inbox-sorhoz (HTML fragmentum)."""
    parts: list[str] = []
    if case.get("category_label"):
        parts.append(theme.badge_html("category", case["category_label"]))
    if case.get("priority") == "surgos":
        parts.append(theme.badge_html("priority", "surgos"))
    confidence = case.get("confidence")
    if confidence is not None:
        parts.append(theme.badge_html("confidence", f"Konf {confidence:.2f}"))
    if case.get("escalated"):
        parts.append(theme.badge_html("escalation", "âš  EszkalĂˇciĂł"))
    if case.get("channel_label"):
        parts.append(theme.badge_html("channel", case["channel_label"]))
    if case.get("status_label"):
        parts.append(theme.badge_html("status", case["status_label"]))
    return " ".join(parts)


def card(title: str | None = None):
    """One-kĂˇrtya kontĂ©ner context managerkĂ©nt: `with components.card('CĂ­m'):`."""
    container = st.container(border=True)
    if title:
        container.markdown(
            f"<div class='one-card__title'>{title}</div>", unsafe_allow_html=True
        )
    return container


_NAV_ICONS: dict[str, str] = {
    "Inbox": "đź“Ą",
    "Ăšj ĂĽgy": "âśŹď¸Ź",
    "Copilot": "đź’¬",
    "Evaluation": "đź“Š",
    "Supervisor": "đź›ˇď¸Ź",
}


def top_header(username: str, role: str, aszf_version: str, provider: str) -> None:
    """One fejlĂ©c-sĂˇv: logĂł, alkalmazĂˇsnĂ©v, ĂSZF-verziĂł, modell-profil, user."""
    provider_label = "â FelhĹ‘" if provider == "cloud" else "đź–Ą On-prem"
    st.markdown(
        "<div class='one-header'>"
        "<span class='one-logo'>one</span>"
        "<b style='font-size:16px;color:var(--one-ink)'>ĂSZF Copilot</b>"
        f"<span style='margin-left:auto;color:var(--one-grey);font-size:13px'>"
        f"ĂSZF {aszf_version or 'â€”'} Â· {provider_label} Â· đź‘¤ {username} ({role})"
        "</span></div>",
        unsafe_allow_html=True,
    )


def icon_nav(items: list[str]) -> str:
    """FĂĽggĹ‘leges ikonos navigĂˇciĂł a sidebarban; a kivĂˇlasztott menĂĽpont neve."""
    labels = [f"{_NAV_ICONS.get(item, 'â€˘')}  {item}" for item in items]
    picked = st.sidebar.radio("NavigĂˇciĂł", labels, label_visibility="collapsed")
    return items[labels.index(picked)]


_STEP_LABELS: dict[str, str] = {
    "language": "Nyelv / tĂ­pus",
    "mask": "MaszkolĂˇs",
    "classify": "OsztĂˇlyozĂˇs",
    "priority": "PrioritĂˇs",
    "policy_map": "SzabĂˇlyzat-tĂ©rkĂ©p",
    "escalation": "EszkalĂˇciĂł",
    "draft": "Draft",
    "verify": "EllenĹ‘rzĂ©s",
}


def _step_state_icon(step: str, output: dict[str, Any]) -> str:
    if step == "escalation" and output.get("required"):
        return "âš "
    if step == "verify" and output.get("ungrounded_count", 0) > 0:
        return "âš "
    return "âś“"


def render_timeline_one(timeline: list[dict[str, Any]], expanded: bool = True) -> None:
    """BecsukhatĂł (alapbĂłl nyitott) One agent-idĹ‘vonal, kattinthatĂł lĂ©pĂ©sekkel."""
    with st.expander("âš™ď¸Ź Agent-idĹ‘vonal", expanded=expanded):
        if not timeline:
            st.info("Az agent mĂ©g nem futott le.")
            return
        for entry in timeline:
            step = entry.get("step", "â€”")
            output = entry.get("output", {}) or {}
            icon = _step_state_icon(step, output)
            label = _STEP_LABELS.get(step, step)
            with st.expander(f"{icon}  {label}", expanded=icon == "âš "):
                st.json(output)


def render_kpi_grid(items: list[tuple[str, str, str]], per_row: int = 3) -> None:
    """KPI-kĂˇrtyĂˇk rĂˇcsban. Minden elem: (label, value, status[ok|warn|bad])."""
    for start in range(0, len(items), per_row):
        row = items[start : start + per_row]
        cols = st.columns(per_row)
        for col, (label, value, status) in zip(cols, row):
            col.markdown(theme.kpi_card_html(label, value, status), unsafe_allow_html=True)

