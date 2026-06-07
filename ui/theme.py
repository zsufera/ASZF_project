from __future__ import annotations

import streamlit as st

# One Magyarország design tokenek (türkiz/fekete/fehér).
# A pontos márka-hex ide cserélhető, ha rendelkezésre áll a márkakönyvi kód.
TOKENS: dict[str, str] = {
    "turq": "#16C7C0",
    "turq_d": "#0FA39D",
    "turq_l": "#E3FAF8",
    "black": "#0E1212",
    "ink": "#16201F",
    "grey": "#6B7A79",
    "line": "#E2EAE9",
    "canvas": "#F7FAF9",
}

_BADGE_STYLES: dict[str, str] = {
    "category": "one-badge one-badge--cat",
    "priority": "one-badge one-badge--prio",
    "escalation": "one-badge one-badge--esc",
    "confidence": "one-badge one-badge--conf",
    "sla": "one-badge one-badge--sla",
    "channel": "one-badge one-badge--chan",
    "status": "one-badge one-badge--status",
}


def badge_html(kind: str, value: str) -> str:
    """One-stílusú színkódolt badge HTML-fragmentum."""
    cls = _BADGE_STYLES.get(kind, "one-badge")
    label = value
    if kind == "priority" and value == "surgos":
        label = "● SÜRGŐS"
    return f'<span class="{cls}">{label}</span>'


def chip_html(text: str) -> str:
    """Kis türkiz forrás-chip (pl. citation)."""
    return f'<span class="one-chip">{text}</span>'


def source_card_html(section: str, dok_tipus: str, quote: str) -> str:
    """Forrás-kártya HTML-fragmentum (§, dok_tipus, idézet)."""
    return (
        '<div class="one-src">'
        f'<div class="one-src__sec">{section} · {dok_tipus}</div>'
        f'<div class="one-src__q">„{quote}"</div>'
        "</div>"
    )


def kpi_card_html(label: str, value: str, status: str = "ok") -> str:
    """KPI-kártya HTML (status: ok|warn|bad → zöld/sárga/piros sáv)."""
    return (
        f'<div class="one-kpi one-kpi--{status}">'
        f'<div class="one-kpi__val">{value}</div>'
        f'<div class="one-kpi__lbl">{label}</div>'
        "</div>"
    )


def theme_css() -> str:
    """A teljes One téma CSS-e <style> blokként (egyszer injektálandó)."""
    t = TOKENS
    return f"""<style>
:root {{
  --one-turq: {t['turq']}; --one-turq-d: {t['turq_d']}; --one-turq-l: {t['turq_l']};
  --one-black: {t['black']}; --one-ink: {t['ink']}; --one-grey: {t['grey']};
  --one-line: {t['line']}; --one-canvas: {t['canvas']};
}}
.stApp {{ background: var(--one-canvas); }}
.one-badge {{ display:inline-block; font-size:11px; padding:2px 9px; border-radius:12px;
  font-weight:700; margin-right:5px; }}
.one-badge--cat {{ background: var(--one-turq-l); color: var(--one-turq-d); }}
.one-badge--prio {{ background:#fde2e1; color:#b42318; }}
.one-badge--esc {{ background:#fff0db; color:#b96a00; }}
.one-badge--conf {{ background:#fef7d6; color:#8a6d00; }}
.one-badge--sla {{ background:#fff; border:1px solid var(--one-line); color:var(--one-ink); }}
.one-badge--chan {{ background:#eef3f2; color:var(--one-grey); }}
.one-badge--status {{ background:#eef3f2; color:var(--one-grey); }}
.one-chip {{ display:inline-block; font-size:10px; background:var(--one-turq-l);
  color:var(--one-turq-d); border:1px solid var(--one-turq); border-radius:10px;
  padding:0 7px; font-weight:600; margin:0 2px; }}
.one-card {{ background:#fff; border:1px solid var(--one-line); border-radius:12px;
  padding:12px; margin-bottom:10px; }}
.one-src {{ border-left:3px solid var(--one-turq); background:#FbFdfd;
  border-radius:0 8px 8px 0; padding:7px 9px; margin-bottom:7px; }}
.one-src__sec {{ font-weight:700; color:var(--one-turq-d); font-size:12px; }}
.one-src__q {{ color:#33403f; font-style:italic; font-size:12px; }}
.one-kpi {{ background:#fff; border:1px solid var(--one-line); border-radius:12px;
  padding:12px; border-top:4px solid var(--one-grey); }}
.one-kpi--ok {{ border-top-color:#22a06b; }}
.one-kpi--warn {{ border-top-color:#e0a400; }}
.one-kpi--bad {{ border-top-color:#d64545; }}
.one-kpi__val {{ font-size:22px; font-weight:800; color:var(--one-ink); }}
.one-kpi__lbl {{ font-size:11px; color:var(--one-grey); text-transform:uppercase;
  letter-spacing:.04em; }}
.one-header {{ display:flex; align-items:center; gap:12px; padding:6px 4px 12px;
  border-bottom:1px solid var(--one-line); margin-bottom:14px; }}
.one-logo {{ display:inline-flex; align-items:center; justify-content:center;
  width:30px; height:30px; border-radius:50%; border:2px solid var(--one-turq);
  color:var(--one-turq); font-style:italic; font-weight:700; font-size:13px; }}
.one-casehdr {{ background:linear-gradient(90deg, var(--one-turq-l), #fff);
  border:1px solid var(--one-line); border-radius:12px; padding:11px 14px;
  margin-bottom:12px; }}
mark {{ background:#FFF3B0; border-radius:3px; padding:0 2px; }}
</style>"""


def inject_theme() -> None:
    """Egyszer hívandó az app tetején: bekeveri a One CSS-t."""
    if not st.session_state.get("_one_theme_injected"):
        st.markdown(theme_css(), unsafe_allow_html=True)
        st.session_state["_one_theme_injected"] = True
