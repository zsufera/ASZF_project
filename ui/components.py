from __future__ import annotations

from typing import Any

import streamlit as st

from ui import theme


def priority_badge(priority: str | None) -> str:
    if priority == "surgos":
        return "🔴 SÜRGŐS"
    return "⚪ normál"


def escalation_badge(escalated: bool) -> str:
    return "⚠ ESZKALÁLT" if escalated else ""


def confidence_badge(confidence: float | None, threshold: float = 0.75) -> str:
    if confidence is None:
        return "Konfidencia: —"
    color = "🟢" if confidence >= threshold else "🟡"
    return f"{color} Konf: {confidence:.2f}"


def sla_badge(days_remaining: int | None) -> str:
    if days_remaining is None:
        return "SLA: —"
    if days_remaining <= 3:
        return f"🔴 SLA: {days_remaining} nap"
    if days_remaining <= 7:
        return f"🟡 SLA: {days_remaining} nap"
    return f"🟢 SLA: {days_remaining} nap"


def render_case_header(case: dict[str, Any]) -> None:
    cols = st.columns([2, 1, 1, 1, 1])
    cols[0].markdown(f"### Ügy `{case.get('case_id')}`")
    cols[1].markdown(f"**{case.get('category_label', '—')}**")
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
        st.info("Nincs forrás a megjelenítéshez.")
        return
    for item in items:
        chunk_id = item.get("chunk_id", "—")
        dok_tipus = item.get("dok_tipus", "ÁSZF")
        paragrafus = item.get("paragrafus") or item.get("paragrafus_szam") or "—"
        quote = item.get("idezet") or item.get("quote") or ""
        with st.expander(f"§{paragrafus} · {dok_tipus} · `{chunk_id}`", expanded=False):
            st.markdown(f"> {quote}")
            if show_plain and item.get("kozertheto_magyarazat"):
                st.markdown(f"**Közérthető magyarázat:** {item['kozertheto_magyarazat']}")
            elif show_plain:
                st.caption("Közérthető magyarázat: a POC determinisztikus policy-map alapján.")


def render_timeline(timeline: list[dict[str, Any]]) -> None:
    if not timeline:
        st.info("Az agent még nem futott le.")
        return
    for entry in timeline:
        step = entry.get("step", "—")
        output = entry.get("output", {})
        warning = ""
        if step == "escalation" and output.get("required"):
            warning = " ⚠"
        elif step == "verify" and output.get("ungrounded_count", 0) > 0:
            warning = " ⚠"
        with st.expander(f"{step}{warning}", expanded=step in {"escalation", "verify"}):
            st.json(output)


def render_history_panel(address: str | None) -> None:
    if not address:
        st.info("Nincs feladó-cím az előzményekhez.")
        return
    from ui import api_client

    try:
        history = api_client.get_history(address)
    except api_client.ApiError as exc:
        st.warning(str(exc))
        return
    if history.get("is_repeated"):
        st.warning("Ismétlődő panasz jelzés az előzmények alapján.")
    items = history.get("items") or []
    if not items:
        st.info("Nincs korábbi üzenet ehhez a címhez.")
        return
    for item in items:
        st.markdown(
            f"- **{item.get('date', '')[:10]}** · {item.get('subject', '')[:80]} "
            f"· {item.get('category', '—')} · `{item.get('status', '')}`"
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
    """Színkódolt One badge-sor egy ügyhöz/inbox-sorhoz (HTML fragmentum)."""
    parts: list[str] = []
    if case.get("category_label"):
        parts.append(theme.badge_html("category", case["category_label"]))
    if case.get("priority") == "surgos":
        parts.append(theme.badge_html("priority", "surgos"))
    confidence = case.get("confidence")
    if confidence is not None:
        parts.append(theme.badge_html("confidence", f"Konf {confidence:.2f}"))
    if case.get("escalated"):
        parts.append(theme.badge_html("escalation", "⚠ Eszkaláció"))
    if case.get("channel_label"):
        parts.append(theme.badge_html("channel", case["channel_label"]))
    if case.get("status_label"):
        parts.append(theme.badge_html("status", case["status_label"]))
    return " ".join(parts)


def card(title: str | None = None):
    """One-kártya konténer context managerként: `with components.card('Cím'):`."""
    container = st.container(border=True)
    if title:
        container.markdown(
            f"<div class='one-card__title'>{title}</div>", unsafe_allow_html=True
        )
    return container


_NAV_ICONS: dict[str, str] = {
    "Inbox": "📥",
    "Új ügy": "✏️",
    "Copilot": "💬",
    "Evaluation": "📊",
    "Supervisor": "🛡️",
}


def top_header(username: str, role: str, aszf_version: str, provider: str) -> None:
    """One fejléc-sáv: logó, alkalmazásnév, ÁSZF-verzió, modell-profil, user."""
    provider_label = "☁ Felhő" if provider == "cloud" else "🖥 On-prem"
    st.markdown(
        "<div class='one-header'>"
        "<span class='one-logo'>one</span>"
        "<b style='font-size:16px;color:var(--one-ink)'>ÁSZF Copilot</b>"
        f"<span style='margin-left:auto;color:var(--one-grey);font-size:13px'>"
        f"ÁSZF {aszf_version or '—'} · {provider_label} · 👤 {username} ({role})"
        "</span></div>",
        unsafe_allow_html=True,
    )


def icon_nav(items: list[str]) -> str:
    """Függőleges ikonos navigáció a sidebarban; a kiválasztott menüpont neve."""
    labels = [f"{_NAV_ICONS.get(item, '•')}  {item}" for item in items]
    picked = st.sidebar.radio("Navigáció", labels, label_visibility="collapsed")
    return items[labels.index(picked)]


_STEP_LABELS: dict[str, str] = {
    "language": "Nyelv / típus",
    "mask": "Maszkolás",
    "classify": "Osztályozás",
    "priority": "Prioritás",
    "policy_map": "Szabályzat-térkép",
    "escalation": "Eszkaláció",
    "draft": "Draft",
    "verify": "Ellenőrzés",
}


def _step_state_icon(step: str, output: dict[str, Any]) -> str:
    if step == "escalation" and output.get("required"):
        return "⚠"
    if step == "verify" and output.get("ungrounded_count", 0) > 0:
        return "⚠"
    return "✓"


def render_timeline_one(timeline: list[dict[str, Any]], expanded: bool = True) -> None:
    """Becsukható (alapból nyitott) One agent-idővonal, kattintható lépésekkel."""
    with st.expander("⚙️ Agent-idővonal", expanded=expanded):
        if not timeline:
            st.info("Az agent még nem futott le.")
            return
        for entry in timeline:
            step = entry.get("step", "—")
            output = entry.get("output", {}) or {}
            icon = _step_state_icon(step, output)
            label = _STEP_LABELS.get(step, step)
            with st.expander(f"{icon}  {label}", expanded=icon == "⚠"):
                st.json(output)


def render_kpi_grid(items: list[tuple[str, str, str]], per_row: int = 3) -> None:
    """KPI-kártyák rácsban. Minden elem: (label, value, status[ok|warn|bad])."""
    for start in range(0, len(items), per_row):
        row = items[start : start + per_row]
        cols = st.columns(per_row)
        for col, (label, value, status) in zip(cols, row):
            col.markdown(theme.kpi_card_html(label, value, status), unsafe_allow_html=True)
