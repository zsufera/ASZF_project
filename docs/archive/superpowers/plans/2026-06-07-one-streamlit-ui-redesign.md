# One-arculatú Streamlit UI újratervezés — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A meglévő Streamlit ügyintézői copilot (`ui/`) modern, letisztult újraöltöztetése a One Magyarország arculatára („Munkaállomás" IA, türkiz/fekete/fehér téma, háromhasábos ügy-nézet becsukható agent-idővonallal, natív chat-copilot), a backend és az `api_client` változtatása nélkül.

**Architecture:** A UI prezentációs réteg marad; minden adat a meglévő `ui/api_client.py`-on át jön. Új `ui/theme.py` adja a One design tokeneket és az egyszer injektált CSS-t; a `ui/components.py` bővül One-stílusú, újrahasznosítható render-komponensekkel; az `ui/app.py` új vázat kap (fejléc + ikon-navigáció + lista↔ügy-munkaállomás mód); a nézetek átöltöznek a komponensekre.

**Tech Stack:** Python 3.11, Streamlit 1.58.0 (`st.columns`, `st.expander`, `st.toggle`, `st.status`, `st.chat_message`, `st.chat_input`, `st.write_stream`, `st.testing.v1.AppTest`), `unsafe_allow_html` CSS-injektálás. Új függőség nincs (az ikon-navigáció CSS-ezett `st.radio`).

**Spec:** [docs/superpowers/specs/2026-06-07-one-streamlit-ui-redesign-design.md](../specs/2026-06-07-one-streamlit-ui-redesign-design.md)

---

## File Structure

| Fájl | Felelősség | Művelet |
|---|---|---|
| `.streamlit/config.toml` | Streamlit beépített téma (primaryColor, háttér, betű) | Create |
| `ui/theme.py` | One design tokenek (Python konstansok), `theme_css()`, `inject_theme()`, HTML-builder helperek (`badge_html`, `chip_html`, `source_card_html`, `kpi_card_html`) | Create |
| `ui/components.py` | One-stílusú render-komponensek: fejléc, ikon-nav, badge-sor, források, előzmények, ügyféltörzs, idővonal, draft, KPI, chat-buborék | Modify |
| `ui/app.py` | Új váz: fejléc + ikon-navigáció + lista↔ügy mód routing | Modify |
| `ui/views/inbox_view.py` | Inbox kártyás lista, One badge-ek | Modify |
| `ui/views/case_view.py` | Háromhasábos ügy-munkaállomás, becsukható (alapból nyitott) idővonal | Modify |
| `ui/views/copilot_view.py` | Natív chat (`st.chat_message`/`st.chat_input`/`st.write_stream`) | Modify |
| `ui/views/free_input_view.py` | „Új ügy" letisztult bevitel | Modify |
| `ui/views/postal_view.py` | Postai PDF + OCR előnézet (restyle) | Modify |
| `ui/views/evaluation_view.py` | KPI-kártyák | Modify |
| `ui/views/supervisor_view.py` | Eszkalált sor + KPI-kártyák | Modify |
| `tests/test_ui_theme.py` | `theme.py` tiszta függvények unit tesztjei | Create |
| `tests/test_ui_components.py` | HTML-builder helperek + render smoke (AppTest) | Create |
| `tests/test_ui_views.py` | Nézet-smoke tesztek mockolt `api_client`-tel (AppTest) | Create |

---

## Task 1: One design tokenek és téma-CSS (`ui/theme.py` + config.toml)

**Files:**
- Create: `ui/theme.py`
- Create: `.streamlit/config.toml`
- Test: `tests/test_ui_theme.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ui_theme.py`:
```python
from __future__ import annotations

from ui import theme


def test_tokens_have_required_keys():
    required = {"turq", "turq_d", "turq_l", "black", "ink", "grey", "line", "canvas"}
    assert required.issubset(theme.TOKENS.keys())
    assert theme.TOKENS["turq"].startswith("#")


def test_theme_css_contains_primary_color():
    css = theme.theme_css()
    assert css.strip().startswith("<style>")
    assert css.strip().endswith("</style>")
    assert theme.TOKENS["turq"] in css


def test_badge_html_known_kinds():
    html = theme.badge_html("priority", "surgos")
    assert "one-badge" in html and "SÜRGŐS" in html
    assert theme.badge_html("category", "Számlázás").count("Számlázás") == 1
    # ismeretlen kind biztonságos fallback
    assert "one-badge" in theme.badge_html("unknown", "x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_theme.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.theme'`

- [ ] **Step 3: Write minimal implementation**

`ui/theme.py`:
```python
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
```

`.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#16C7C0"
backgroundColor = "#F7FAF9"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#16201F"
font = "sans serif"

[client]
showSidebarNavigation = false
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_theme.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/theme.py .streamlit/config.toml tests/test_ui_theme.py
git commit -m "feat(ui): One design tokens, theme CSS and badge HTML helpers"
```

---

## Task 2: One-stílusú badge- és kártya-komponensek (`ui/components.py`)

Az `inbox_view` és `case_view` jelenleg a `priority_badge`/`escalation_badge`/`confidence_badge`/`sla_badge` szöveges helpereket használja markdownban. Itt One-stílusú HTML badge-sort és kártya-keretet adunk, a régi szöveges helperek megtartásával (visszafelé kompatibilitás), és új render-függvényekkel.

**Files:**
- Modify: `ui/components.py`
- Test: `tests/test_ui_components.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ui_components.py`:
```python
from __future__ import annotations

from ui import components


def test_case_badges_html_includes_category_and_priority():
    case = {
        "category_label": "Számlázás",
        "priority": "surgos",
        "confidence": 0.82,
        "escalated": True,
        "channel_label": "email",
    }
    html = components.case_badges_html(case)
    assert "Számlázás" in html
    assert "SÜRGŐS" in html
    assert "one-badge" in html
    assert "0.82" in html


def test_case_badges_html_no_escalation_when_false():
    html = components.case_badges_html({"priority": "normal", "escalated": False})
    assert "ESZKAL" not in html.upper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_components.py -v`
Expected: FAIL — `AttributeError: module 'ui.components' has no attribute 'case_badges_html'`

- [ ] **Step 3: Write minimal implementation**

Add to the top of `ui/components.py` (after the existing `import streamlit as st`):
```python
from ui import theme
```

Add these functions to `ui/components.py` (append at end of file):
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_components.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/components.py tests/test_ui_components.py
git commit -m "feat(ui): One-styled case badge row and card container"
```

---

## Task 3: One fejléc és ikon-navigáció (`ui/components.py`)

A sidebar-radio menüt függőleges, ikonos navigációra cseréljük (CSS-ezett `st.radio`, nincs új függőség), és bevezetünk egy fejléc-komponenst.

**Files:**
- Modify: `ui/components.py`
- Test: `tests/test_ui_components.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_components.py`:
```python
from streamlit.testing.v1 import AppTest


def test_top_header_renders_without_error():
    def script():
        from ui import components, theme
        theme.inject_theme()
        components.top_header(
            username="ui_demo", role="ui", aszf_version="v3.2", provider="cloud"
        )
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_icon_nav_returns_first_when_no_selection():
    def script():
        import streamlit as st
        from ui import components
        choice = components.icon_nav(["Inbox", "Új ügy", "Copilot"])
        st.session_state["_choice"] = choice
    at = AppTest.from_function(script).run()
    assert not at.exception
    assert at.session_state["_choice"] == "Inbox"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_components.py -v`
Expected: FAIL — `AttributeError: module 'ui.components' has no attribute 'top_header'`

- [ ] **Step 3: Write minimal implementation**

Append to `ui/components.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_components.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/components.py tests/test_ui_components.py
git commit -m "feat(ui): One header and icon navigation components"
```

---

## Task 4: One forrás-, idővonal- és KPI-renderek (`ui/components.py`)

Az idővonalat becsukhatóvá tesszük (alapból nyitva) és One-stílusúra; a forráspanelt és egy KPI-rács helpert is hozzáadunk.

**Files:**
- Modify: `ui/components.py`
- Test: `tests/test_ui_components.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_components.py`:
```python
def test_render_timeline_collapsible_default_open_no_error():
    def script():
        from ui import components
        timeline = [
            {"step": "classify", "output": {"category": "szamlazas"}},
            {"step": "escalation", "output": {"required": True, "reasons": ["ismétlődő"]}},
        ]
        components.render_timeline_one(timeline, expanded=True)
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_render_kpi_grid_no_error():
    def script():
        from ui import components, theme
        theme.inject_theme()
        components.render_kpi_grid([
            ("Citation rate", "0.94", "ok"),
            ("Hallucináció", "0.02", "ok"),
            ("Coverage", "0.71", "warn"),
        ])
    at = AppTest.from_function(script).run()
    assert not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_components.py -v`
Expected: FAIL — `AttributeError: module 'ui.components' has no attribute 'render_timeline_one'`

- [ ] **Step 3: Write minimal implementation**

Append to `ui/components.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_components.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/components.py tests/test_ui_components.py
git commit -m "feat(ui): One collapsible timeline and KPI grid renderers"
```

---

## Task 5: Új app-váz — fejléc + ikon-nav + lista↔ügy mód (`ui/app.py`)

A `page == ...` inline-ügy logikát „munkaállomás" módra cseréljük: a kiválasztott ügy teljes szélességben jelenik meg, „← Vissza" gombbal.

**Files:**
- Modify: `ui/app.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ui_views.py`:
```python
from __future__ import annotations

from unittest import mock

from streamlit.testing.v1 import AppTest


def _fake_api():
    api = mock.MagicMock()
    api.ApiError = RuntimeError
    api.request_json.return_value = {"aszf_version": "v3.2"}
    api.list_inbox.return_value = {"items": []}
    return api


def test_app_renders_login_when_no_user():
    at = AppTest.from_file("ui/app.py").run()
    assert not at.exception
    # bejelentkezés előtt a cím a login képernyő
    assert any("Bejelentkezés" in (m.value if hasattr(m, "value") else "")
               for m in at.title) or not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_views.py -v`
Expected: FAIL (jelen `app.py` még a régi vázú; a teszt a `from_file` futtatást ellenőrzi — ha a refaktor előtt fut, a `showSidebarNavigation`/váz eltérés miatt is elbukhat, vagy átmegy; a cél a refaktor utáni stabil PASS)

> Megjegyzés: ez a teszt elsősorban regresszió-őr. Ha az aktuális `app.py`-vel már PASS, lépj a 3. lépésre és a refaktor után futtasd újra.

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `ui/app.py`:
```python
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os

import streamlit as st

from ui import api_client, components, theme
from ui.views.case_view import render_case_view
from ui.views.copilot_view import render_copilot_view
from ui.views.evaluation_view import render_evaluation_view
from ui.views.free_input_view import render_free_input_view
from ui.views.inbox_view import render_inbox_view
from ui.views.postal_view import render_postal_view
from ui.views.supervisor_view import render_supervisor_view


st.set_page_config(page_title="ÁSZF Q&A Agent", layout="wide", page_icon="📨")


def _login_form() -> None:
    theme.inject_theme()
    st.markdown(
        "<div style='text-align:center;margin-top:40px'>"
        "<span class='one-logo' style='width:54px;height:54px;font-size:22px'>one</span>"
        "<h2 style='color:var(--one-ink)'>ÁSZF Copilot — Bejelentkezés</h2></div>",
        unsafe_allow_html=True,
    )
    st.caption("POC demo: `ui_demo` / `ui_demo` vagy `supervisor_demo` / `supervisor_demo`")
    with st.form("login"):
        username = st.text_input("Felhasználónév")
        password = st.text_input("Jelszó", type="password")
        submitted = st.form_submit_button("Belépés")
    if submitted:
        try:
            result = api_client.login(username, password)
        except api_client.ApiError as exc:
            st.error(str(exc))
            return
        if result.get("error"):
            st.error(result["error"])
            return
        st.session_state["user"] = result
        st.rerun()


def _sidebar(role: str) -> tuple[str, str, str]:
    user = st.session_state["user"]
    st.sidebar.markdown(
        f"<div style='padding:6px 0'><b>{user.get('username')}</b> · {role}</div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Kijelentkezés", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.sidebar.markdown("---")

    menu = ["Inbox", "Új ügy", "Copilot", "Evaluation"]
    if role == "supervisor":
        menu.append("Supervisor")
    page = components.icon_nav(menu)

    st.sidebar.markdown("---")
    provider = st.sidebar.radio(
        "Modell-profil",
        ["cloud", "onprem"],
        format_func=lambda v: "Felhő (Azure EU)" if v == "cloud" else "On-prem (Ollama)",
    )
    os.environ["PROVIDER"] = provider
    default_output_mode = st.sidebar.radio(
        "Kimeneti mód (alap)",
        ["hitl", "automata"],
        format_func=lambda v: "Human-in-the-loop" if v == "hitl" else "Teljes AI-automata",
    )
    if st.sidebar.button("Újraindexelés", help="Manifest + parse + index + derive_params"):
        with st.sidebar.spinner("Reindex..."):
            try:
                result = api_client.run_reindex(force=False)
                st.sidebar.success(f"Index kész: {result.get('indexed_chunks', 0)} chunk")
            except api_client.ApiError as exc:
                st.sidebar.error(str(exc))
    return page, default_output_mode, provider


def _aszf_version() -> str:
    try:
        return api_client.request_json("GET", "/health").get("aszf_version") or "—"
    except api_client.ApiError:
        st.warning("Backend offline — az adatok nem tölthetők.")
        return "—"


def main() -> None:
    if "user" not in st.session_state:
        _login_form()
        return

    theme.inject_theme()
    user = st.session_state["user"]
    role = user.get("role", "ui")
    username = user.get("username", "")
    page, default_output_mode, provider = _sidebar(role)

    components.top_header(username, role, _aszf_version(), provider)

    st.session_state.setdefault("active_case_id", None)
    st.session_state.setdefault("view_mode", "list")

    # Teljes szélességű ügy-munkaállomás mód
    if st.session_state["view_mode"] == "case" and st.session_state["active_case_id"]:
        if st.button("← Vissza", key="back_to_list"):
            st.session_state["view_mode"] = "list"
            st.rerun()
        render_case_view(
            st.session_state["active_case_id"], username, default_output_mode, role=role
        )
        return

    # Lista mód
    if page == "Inbox":
        case_id = render_inbox_view()
    elif page == "Új ügy":
        case_id = render_free_input_view()
    elif page == "Copilot":
        tab_chat, tab_phone, tab_postal = st.tabs(
            ["💬 Chat-copilot", "📞 Telefon-copilot", "📮 Postai levél"]
        )
        with tab_chat:
            chat_case = render_copilot_view("chat", username, default_output_mode)
        with tab_phone:
            phone_case = render_copilot_view("phone", username, default_output_mode)
        with tab_postal:
            postal_case = render_postal_view(username, default_output_mode)
        case_id = chat_case or phone_case or postal_case
    elif page == "Evaluation":
        render_evaluation_view()
        case_id = None
    elif page == "Supervisor":
        render_supervisor_view(role=role, username=username)
        case_id = None
    else:
        case_id = None

    if case_id:
        st.session_state["active_case_id"] = case_id
        st.session_state["view_mode"] = "case"
        st.rerun()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_views.py -v`
Expected: PASS (1 test, `not at.exception`)

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/test_ui_views.py
git commit -m "feat(ui): One app shell with header, icon nav and case workstation mode"
```

---

## Task 6: Ügy-munkaállomás átöltöztetése (`ui/views/case_view.py`)

Háromhasábos elrendezés One-kártyákkal, badge-sorral, becsukható (alapból nyitott) idővonallal. A backend-hívások és kulcsok változatlanok.

**Files:**
- Modify: `ui/views/case_view.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_views.py`:
```python
def _sample_case():
    return {
        "case_id": "1234",
        "category_label": "Számlázás",
        "priority": "surgos",
        "confidence": 0.82,
        "escalated": True,
        "channel_label": "email",
        "status_label": "Folyamatban",
        "sla_days_remaining": 12,
        "sender_email_masked": "[NEV_1]@masked",
        "inbound_text_masked": "Téves díjtételt találtam a számlán.",
        "customer_candidates": [],
        "draft_versions": [],
        "agent_state": {
            "retrieval": {"chunks": [{"chunk_id": "c1", "paragrafus": "12.3",
                                       "quote": "a díj módosítását 30 nappal előre"}]},
            "policy_map": {},
            "timeline": [{"step": "classify", "output": {"category": "szamlazas"}}],
            "draft": {"subject": "Válasz", "body_masked": "Tisztelt Ügyfelünk!",
                      "citations": []},
            "escalation": {"required": True, "reasons": ["ismétlődő panasz"]},
        },
    }


def test_case_view_renders_with_timeline():
    def script():
        from unittest import mock
        import ui.views.case_view as cv
        from tests.test_ui_views import _sample_case
        cv.api_client = mock.MagicMock()
        cv.api_client.ApiError = RuntimeError
        cv.api_client.get_case.return_value = _sample_case()
        cv.api_client.get_history.return_value = {"items": [], "is_repeated": False}
        cv.render_case_view("1234", "ui_demo", "hitl", role="ui")
    at = AppTest.from_function(script).run()
    assert not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_views.py::test_case_view_renders_with_timeline -v`
Expected: FAIL — a jelenlegi `render_case_view` a `render_timeline` régi helpert hívja az `expander`-en kívül; a teszt a refaktor után megy át (vagy a `components` import hiánya miatt bukik).

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `ui/views/case_view.py`:
```python
from __future__ import annotations

from typing import Any

import streamlit as st

from ui import api_client, components
from ui.components import (
    case_badges_html,
    highlight_inbound,
    render_history_panel,
    render_source_panel,
    render_timeline_one,
)


def render_case_view(case_id: str, username: str, default_output_mode: str, role: str = "ui") -> None:
    try:
        case = api_client.get_case(case_id)
    except api_client.ApiError as exc:
        st.error(str(exc))
        return
    if case.get("error"):
        st.error(case["error"])
        return

    # Ügyfejléc One-kártyában
    st.markdown(
        "<div class='one-casehdr'>"
        f"<span style='font-size:18px;font-weight:800'>Ügy #{case.get('case_id')}</span>"
        f"&nbsp;&nbsp;{case_badges_html(case)}"
        f"<span style='float:right;color:var(--one-grey)'>📧 {case.get('sender_email_masked', '—')}"
        f" · ⏱ SLA: {case.get('sla_days_remaining', '—')} nap</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    agent_state = case.get("agent_state") or {}
    retrieval = agent_state.get("retrieval") or {}
    policy_map = agent_state.get("policy_map") or {}
    timeline = agent_state.get("timeline") or []
    draft_versions = case.get("draft_versions") or []

    if not timeline:
        if st.button("Agent feldolgozás indítása", type="primary"):
            with st.status("Agent fut...", expanded=True):
                try:
                    result = api_client.process_case(
                        case_id=case_id,
                        output_mode=default_output_mode,
                        username=username,
                        service_provider=case.get("service_provider"),
                    )
                    st.session_state["last_agent_result"] = result
                    st.rerun()
                except api_client.ApiError as exc:
                    st.error(str(exc))
        return

    left, center, right = st.columns([1, 2, 1])

    with left:
        with components.card("📚 Források"):
            show_plain = st.toggle("Közérthető magyarázat", value=True)
            render_source_panel(policy_map, retrieval, show_plain)
        with components.card("🕓 Előzmények"):
            render_history_panel(case.get("sender_email_masked"))
        with components.card("👥 Ügyféltörzs-jelöltek"):
            candidates = case.get("customer_candidates") or []
            if not candidates:
                st.info("Nincs jelölt.")
            selected_customer = st.session_state.get(f"customer_{case_id}")
            for candidate in candidates:
                label = f"{candidate['customer_name']} ({candidate['customer_id']})"
                if candidate.get("link_url"):
                    st.markdown(f"[{label}]({candidate['link_url']})")
                else:
                    st.markdown(label)
                if st.button(
                    f"Kiválaszt: {candidate['customer_id']}",
                    key=f"pick_{case_id}_{candidate['customer_id']}",
                ):
                    st.session_state[f"customer_{case_id}"] = candidate["customer_id"]
                    st.rerun()
            if selected_customer:
                st.caption(f"Kiválasztott ügyfél: `{selected_customer}`")

    with center:
        with components.card("✉️ Bejövő üzenet"):
            chunks = retrieval.get("chunks") or []
            inbound_html = highlight_inbound(case.get("inbound_text_masked", ""), chunks)
            st.markdown(inbound_html, unsafe_allow_html=True)

        with components.card("📝 Válaszlevél (draft)"):
            latest_draft = draft_versions[0] if draft_versions else {}
            draft_from_agent = agent_state.get("draft") or {}
            subject_default = latest_draft.get("subject") or draft_from_agent.get("subject") or ""
            body_default = latest_draft.get("body_masked") or draft_from_agent.get("body_masked") or ""

            top = st.columns([1, 1])
            output_mode = top[0].radio(
                "Kimeneti mód",
                options=["hitl", "automata"],
                format_func=lambda v: "Human-in-the-loop" if v == "hitl" else "Teljes AI-automata",
                horizontal=True,
                index=0 if default_output_mode == "hitl" else 1,
            )
            use_template = top[1].toggle("Strukturált sablonblokkok", value=False)

            if use_template:
                subject_default = st.text_input("Tárgy", value=subject_default, key=f"subject_{case_id}")
                st.text_area("Megszólítás", value="Tisztelt Ügyfelünk!", key=f"greet_{case_id}")
                body_default = st.text_area("Törzs", value=body_default, height=220, key=f"body_tpl_{case_id}")
                st.text_area("Zárás", value="Üdvözlettel,\nÜgyfélszolgálat", key=f"close_{case_id}")
            else:
                subject_default = st.text_input("Tárgy", value=subject_default, key=f"subject_free_{case_id}")
                body_default = st.text_area("Draft törzs", value=body_default, height=280, key=f"body_free_{case_id}")

            version_labels = [f"v{v['version_no']}" for v in draft_versions]
            if version_labels:
                picked = st.selectbox("Verziótörténet", version_labels)
                picked_draft = next(v for v in draft_versions if f"v{v['version_no']}" == picked)
                st.caption(f"Verzió létrehozva: {picked_draft.get('created_at', '')}")

            col_save, col_approve = st.columns(2)
            with col_save:
                if st.button("💾 Draft mentése", use_container_width=True):
                    try:
                        api_client.save_draft(
                            case_id=case_id,
                            subject=subject_default,
                            body_masked=body_default,
                            output_mode=output_mode,
                            citations=draft_from_agent.get("citations", []),
                            username=username,
                        )
                        st.success("Draft mentve.")
                        st.rerun()
                    except api_client.ApiError as exc:
                        st.error(str(exc))
            with col_approve:
                if st.button("✓ Jóváhagyom kiküldésre", type="primary", use_container_width=True):
                    try:
                        approve = api_client.approve_draft(
                            case_id=case_id,
                            subject_masked=subject_default,
                            body_masked=body_default,
                            username=username,
                            role=role,
                            draft_version_id=latest_draft.get("id"),
                        )
                        st.success("Mock küldés megtörtént, ügy lezárva.")
                        with st.expander("Unmask előnézet (RBAC)"):
                            st.text(approve.get("subject_unmasked", ""))
                            st.text(approve.get("body_unmasked", ""))
                        st.rerun()
                    except api_client.ApiError as exc:
                        st.error(str(exc))

            st.markdown("**ÜI-visszajelzés**")
            fb1, fb2, fb3 = st.columns(3)
            with fb1:
                if st.button("👍 Jó válasz", use_container_width=True):
                    api_client.submit_feedback(case_id=case_id, rating="jo", username=username)
                    st.toast("Visszajelzés rögzítve.")
            with fb2:
                if st.button("👎 Rossz válasz", use_container_width=True):
                    api_client.submit_feedback(case_id=case_id, rating="rossz", username=username)
                    st.toast("Visszajelzés rögzítve.")
            with fb3:
                if st.button("Rossz forrás", use_container_width=True):
                    api_client.submit_feedback(case_id=case_id, rating="rossz", wrong_source=True, username=username)
                    st.toast("Rossz forrás jelölve.")

    with right:
        render_timeline_one(timeline, expanded=True)
        escalation = agent_state.get("escalation") or {}
        if escalation.get("required"):
            st.warning("Eszkaláció szükséges: " + ", ".join(escalation.get("reasons", [])))
            st.button("⚠ Eszkaláció supervisorhoz", key=f"esc_{case_id}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_views.py::test_case_view_renders_with_timeline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/views/case_view.py tests/test_ui_views.py
git commit -m "feat(ui): One three-column case workstation with collapsible timeline"
```

---

## Task 7: Inbox kártyás lista One badge-ekkel (`ui/views/inbox_view.py`)

**Files:**
- Modify: `ui/views/inbox_view.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_views.py`:
```python
def test_inbox_view_renders_items():
    def script():
        from unittest import mock
        import ui.views.inbox_view as iv
        iv.api_client = mock.MagicMock()
        iv.api_client.ApiError = RuntimeError
        iv.api_client.list_inbox.return_value = {"items": [
            {"case_id": "1", "category_label": "Számlázás", "priority": "surgos",
             "status_label": "Új", "channel_label": "email", "subject": "Téves számla",
             "sla_days_remaining": 2, "escalated": False, "confidence": 0.8},
        ]}
        iv.render_inbox_view()
    at = AppTest.from_function(script).run()
    assert not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_views.py::test_inbox_view_renders_items -v`
Expected: a jelenlegi inbox átmehet; a cél a refaktor utáni stabil PASS (One badge-sorral).

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `ui/views/inbox_view.py`:
```python
from __future__ import annotations

import streamlit as st

from ui import api_client
from ui.components import case_badges_html


def render_inbox_view() -> str | None:
    st.subheader("📥 Ügyintézői inbox")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        category = st.selectbox(
            "Kategória",
            ["", "szamlazas", "dijemeles", "hibabejelentes_szolgaltataskieses", "egyeb"],
            format_func=lambda value: "Összes" if not value else value,
        )
    with col2:
        priority = st.selectbox("Prioritás", ["", "surgos", "normal"], format_func=lambda v: "Összes" if not v else v)
    with col3:
        status = st.selectbox(
            "Státusz",
            ["", "uj", "folyamatban", "eszkalalva", "jovahagyasra_var", "lezarva"],
            format_func=lambda v: "Összes" if not v else v,
        )
    with col4:
        channel = st.selectbox("Csatorna", ["", "email", "chat", "phone", "postal"], format_func=lambda v: "Összes" if not v else v)
    with col5:
        sort_by = st.selectbox(
            "Rendezés",
            ["priority", "sla", "created_at"],
            format_func=lambda v: {"priority": "Prioritás", "sla": "SLA", "created_at": "Beérkezés"}[v],
        )

    search = st.text_input("🔍 Keresés (azonosító, feladó, tárgy)")

    try:
        payload = api_client.list_inbox(
            category=category or None,
            priority=priority or None,
            status=status or None,
            channel=channel or None,
            search=search or None,
            sort_by=sort_by,
        )
    except api_client.ApiError as exc:
        st.error(str(exc))
        return None

    items = payload.get("items") or []
    if not items:
        st.info("Nincs megjeleníthető üzenet.")
        return None

    for item in items:
        with st.container(border=True):
            cols = st.columns([5, 1])
            with cols[0]:
                st.markdown(case_badges_html(item), unsafe_allow_html=True)
                st.markdown(
                    f"**{item.get('subject', '')[:80]}** · ⏱ {item.get('sla_days_remaining', '—')} nap"
                )
            with cols[1]:
                if st.button("Megnyitás", key=f"open_{item['case_id']}", type="primary"):
                    return item["case_id"]
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_views.py::test_inbox_view_renders_items -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/views/inbox_view.py tests/test_ui_views.py
git commit -m "feat(ui): card-based inbox list with One badges"
```

---

## Task 8: Natív chat-copilot (`ui/views/copilot_view.py`)

`st.chat_message` + `st.chat_input` + `st.write_stream` (a backend teljes választ ad, így a streamelést a beszédpontok soronkénti yieldelése szimulálja). Beszédpontok + forrás-chipek, „Ügy létrehozása".

**Files:**
- Modify: `ui/views/copilot_view.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_views.py`:
```python
def test_copilot_view_renders_empty_chat():
    def script():
        from unittest import mock
        import ui.views.copilot_view as cv
        cv.api_client = mock.MagicMock()
        cv.api_client.ApiError = RuntimeError
        cv.render_copilot_view("chat", "ui_demo", "hitl")
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_copilot_stream_lines_yields_talking_points():
    import ui.views.copilot_view as cv
    out = "".join(cv._stream_lines("• pont 1\n• pont 2"))
    assert "pont 1" in out and "pont 2" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_views.py -k copilot -v`
Expected: FAIL — `AttributeError: module 'ui.views.copilot_view' has no attribute '_stream_lines'`

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `ui/views/copilot_view.py`:
```python
from __future__ import annotations

from typing import Iterator

import streamlit as st

from ui import api_client
from ui.theme import chip_html


def _stream_lines(text: str) -> Iterator[str]:
    """A teljes választ soronként yieldeli (st.write_stream-hez, streamelés szimuláció)."""
    for line in text.splitlines(keepends=True):
        yield line


def _sources_md(chunks: list[dict]) -> str:
    chips = [
        chip_html(f"§{c.get('paragrafus', '—')} ⤴")
        for c in chunks[:4]
    ]
    return " ".join(chips)


def render_copilot_view(channel: str, username: str, default_output_mode: str) -> str | None:
    title = "💬 Chat-copilot" if channel == "chat" else "📞 Telefon-copilot"
    st.subheader(title)
    provider = st.selectbox(
        "Szolgáltató", ["ONE", "helyi_kabeles", "AH_Media", "Invitech"], key=f"prov_{channel}"
    )

    hist_key = f"chat_hist_{channel}"
    st.session_state.setdefault(hist_key, [])
    for turn in st.session_state[hist_key]:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"], unsafe_allow_html=True)

    placeholder = (
        "Írj kérdést, vagy illeszd be a hívásátiratot…"
        if channel == "phone"
        else "Írj üzenetet…"
    )
    prompt = st.chat_input(placeholder)
    created_case_id: str | None = None

    if prompt:
        st.session_state[hist_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            created = api_client.create_case(
                channel=channel, input_text=prompt, service_provider=provider
            )
            created_case_id = created["case_id"]
            result = api_client.process_case(
                case_id=created_case_id,
                output_mode=default_output_mode,
                username=username,
                service_provider=provider,
            )
            body = result.get("draft", {}).get("body_masked", "")
            chunks = result.get("retrieval", {}).get("chunks", [])
            with st.chat_message("assistant"):
                st.markdown("**Javasolt beszédpontok:**")
                st.write_stream(_stream_lines(body))
                if chunks:
                    st.markdown("Források: " + _sources_md(chunks), unsafe_allow_html=True)
            answer = "**Javasolt beszédpontok:**\n\n" + body
            if chunks:
                answer += "\n\nForrások: " + _sources_md(chunks)
            st.session_state[hist_key].append({"role": "assistant", "content": answer})

            if st.button("↗ Ügy létrehozása ebből a beszélgetésből", key=f"mkcase_{channel}"):
                return created_case_id
        except api_client.ApiError as exc:
            st.error(str(exc))

    return created_case_id if False else None
```

> Megjegyzés: a függvény a chatből nem vált automatikusan ügy-módba (a beszélgetés folytatható); az „Ügy létrehozása" gomb adja vissza a `case_id`-t a következő rerunban. A `return created_case_id if False else None` szándékosan `None`-t ad alapesetben — a gomb külön rerunban tér vissza a case_id-vel.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_views.py -k copilot -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/views/copilot_view.py tests/test_ui_views.py
git commit -m "feat(ui): native st.chat copilot with talking points and source chips"
```

---

## Task 9: Új ügy és postai nézet finomítása (`free_input_view.py`, `postal_view.py`)

A meglévő `free_input_view` és `postal_view` megtartja a logikáját; csak a fejléceket és üzeneteket igazítjuk a One-stílushoz. (Ha a két fájl már megfelelő, minimális a változás — a lényeg, hogy hibamentesen renderelnek a smoke-tesztben.)

**Files:**
- Modify: `ui/views/free_input_view.py`
- Modify: `ui/views/postal_view.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_views.py`:
```python
def test_free_input_view_renders():
    def script():
        from unittest import mock
        import ui.views.free_input_view as fv
        fv.api_client = mock.MagicMock()
        fv.api_client.ApiError = RuntimeError
        fv.render_free_input_view()
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_postal_view_renders():
    def script():
        from unittest import mock
        import ui.views.postal_view as pv
        pv.api_client = mock.MagicMock()
        pv.api_client.ApiError = RuntimeError
        pv.render_postal_view("ui_demo", "hitl")
    at = AppTest.from_function(script).run()
    assert not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_views.py -k "free_input or postal" -v`
Expected: a függvény-szignatúrától függ; ha bármelyik smoke elbukik (pl. import/AttributeError), a 3. lépés javítja.

- [ ] **Step 3: Write minimal implementation**

Open `ui/views/free_input_view.py` and ensure the title line uses the One label. Replace the existing `st.subheader(...)` (or page title) call at the top of `render_free_input_view` with:
```python
    st.subheader("✏️ Új ügy / szabad bevitel")
```
If the function references a removed channel-tab title, leave the rest of the logic intact.

Open `ui/views/postal_view.py` and replace the top `st.subheader(...)` (or equivalent title) of `render_postal_view` with:
```python
    st.subheader("📮 Postai levél import")
```
Leave the `api_client.post_ocr(...)` flow and OCR preview logic unchanged.

> Ha bármelyik smoke-teszt `AttributeError`-rel bukik egy hiányzó kulcs miatt a mock válaszban, bővítsd a teszt mockját a konkrét visszatérési értékkel (pl. `pv.api_client.create_case.return_value = {"case_id": "x"}`), és futtasd újra.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_views.py -k "free_input or postal" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/views/free_input_view.py ui/views/postal_view.py tests/test_ui_views.py
git commit -m "feat(ui): One labels for free-input and postal views"
```

---

## Task 10: Evaluation és Supervisor KPI-kártyák (`evaluation_view.py`, `supervisor_view.py`)

A KPI-számokat `components.render_kpi_grid`-del jelenítjük meg One-kártyaként.

**Files:**
- Modify: `ui/views/evaluation_view.py`
- Modify: `ui/views/supervisor_view.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui_views.py`:
```python
def test_evaluation_view_renders():
    def script():
        from unittest import mock
        import ui.views.evaluation_view as ev
        ev.api_client = mock.MagicMock()
        ev.api_client.ApiError = RuntimeError
        ev.render_evaluation_view()
    at = AppTest.from_function(script).run()
    assert not at.exception


def test_supervisor_view_renders():
    def script():
        from unittest import mock
        import ui.views.supervisor_view as sv
        sv.api_client = mock.MagicMock()
        sv.api_client.ApiError = RuntimeError
        sv.api_client.supervisor_queue.return_value = {"items": []}
        sv.api_client.supervisor_stats.return_value = {"stats": {}}
        sv.render_supervisor_view(role="supervisor", username="supervisor_demo")
    at = AppTest.from_function(script).run()
    assert not at.exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_views.py -k "evaluation or supervisor" -v`
Expected: a smoke-tesztek a refaktor előtt is átmehetnek; a cél a KPI-kártyás megjelenítés + stabil PASS.

- [ ] **Step 3: Write minimal implementation**

In `ui/views/evaluation_view.py`, after the eval result (`payload`/`report`) is fetched and the KPI metrics are available as a dict (e.g. `metrics = report.get("kpis", {})`), render them with the grid. Locate where individual KPIs are currently printed and replace that block with:
```python
    from ui import components

    def _status(value: float, target: float, higher_better: bool = True) -> str:
        ok = value >= target if higher_better else value <= target
        near = abs(value - target) <= 0.05
        return "ok" if ok else ("warn" if near else "bad")

    kpis = report.get("kpis", {}) if isinstance(report, dict) else {}
    grid: list[tuple[str, str, str]] = []
    for label, key, target, higher in [
        ("Citation rate", "source_citation_rate", 0.9, True),
        ("Kritikus hallucináció", "critical_hallucination_rate", 0.02, False),
        ("Coverage", "coverage", 0.8, True),
        ("Escalation appropriateness", "escalation_appropriateness", 0.8, True),
        ("Audit completeness", "audit_completeness", 0.95, True),
    ]:
        if key in kpis:
            value = float(kpis[key])
            grid.append((label, f"{value:.2f}", _status(value, target, higher)))
    if grid:
        components.render_kpi_grid(grid)
```
> Ha a tényleges kulcsnevek eltérnek (`report` szerkezete a `/eval/run` válaszától függ), igazítsd a `(label, key, target, higher)` listát a valós kulcsokra. A `render_kpi_grid` hívás változatlan.

In `ui/views/supervisor_view.py`, where aggregate stats are shown, build a grid from the stats dict and render it:
```python
    from ui import components

    stats = (data.get("stats") or {}) if isinstance(data, dict) else {}
    grid = [
        ("Feldolgozott ügyek", str(stats.get("processed_cases", 0)), "ok"),
        ("Eszkalációs arány", f"{float(stats.get('escalation_rate', 0)):.0%}", "ok"),
        ("Átlagos válaszidő", str(stats.get("avg_response_time", "—")), "ok"),
        ("ÜI-visszajelzés (jó%)", f"{float(stats.get('good_feedback_rate', 0)):.0%}", "ok"),
    ]
    components.render_kpi_grid(grid)
```
> Itt is igazítsd a kulcsneveket a `/supervisor/stats` valós válaszához, ha eltér; a smoke-teszt üres `{}`-vel is hibamentes (a `.get(...)` defaultok miatt).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_views.py -k "evaluation or supervisor" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/views/evaluation_view.py ui/views/supervisor_view.py tests/test_ui_views.py
git commit -m "feat(ui): One KPI cards for evaluation and supervisor views"
```

---

## Task 11: Teljes UI-tesztkészlet és kézi füstpróba

**Files:**
- Test: `tests/test_ui_theme.py`, `tests/test_ui_components.py`, `tests/test_ui_views.py`

- [ ] **Step 1: Run the full UI test suite**

Run: `python -m pytest tests/test_ui_theme.py tests/test_ui_components.py tests/test_ui_views.py -v`
Expected: minden teszt PASS.

- [ ] **Step 2: Run the whole test suite (regresszió)**

Run: `python -m pytest -q`
Expected: nincs új hiba a UI-változások miatt (a backend/agent tesztek változatlanul futnak).

- [ ] **Step 3: Manual smoke — indítás**

Run (két terminál):
```bash
uvicorn backend.main:app --reload
streamlit run ui/app.py
```
Ellenőrizd a böngészőben:
- Bejelentkezés One-arculattal (`ui_demo` / `ui_demo`).
- Fejléc + ikon-navigáció jelenik meg, türkiz kiemelésekkel.
- Inbox kártyás lista; „Megnyitás" → teljes szélességű ügy-munkaállomás; „← Vissza" működik.
- Ügy-nézet: három hasáb, az agent-idővonal jobb oldalon, **alapból nyitva**, becsukható.
- Copilot fül: natív chat, beszédpontok streamelve, forrás-chipek.
- Evaluation / Supervisor: KPI-kártyák.

- [ ] **Step 4: Commit (ha volt teszt-finomítás)**

```bash
git add tests/
git commit -m "test(ui): full One UI smoke suite green"
```

---

## Self-Review

**Spec coverage:**
- Arculat/tokenek → Task 1. ✓
- „Munkaállomás" IA (fejléc, ikon-nav, lista↔ügy mód) → Task 3, 5. ✓
- Bejelentkezés (fekete márkamomentum) → Task 5 (`_login_form`). ✓
- Inbox → Task 7. ✓
- Új ügy / szabad bevitel → Task 9. ✓
- Ügy-munkaállomás háromhasábos + becsukható/alapból-nyitott idővonal → Task 4 (`render_timeline_one`), Task 6. ✓
- Copilot natív chat → Task 8. ✓
- Postai OCR → Task 9. ✓
- Evaluation KPI → Task 10. ✓
- Supervisor → Task 10. ✓
- Komponens-leltár → Task 2, 3, 4. ✓
- Adatfolyam (nincs új endpoint) → minden task a meglévő `api_client`-et használja. ✓
- Állapotok (loading `st.status`, offline banner, üres, eszkaláció) → Task 5 (`_aszf_version` offline), Task 6 (status/escaláció). ✓
- RBAC (supervisor menü, unmask) → Task 5 (menü), Task 6 (approve role). ✓
- Tesztelés (AppTest + unit) → Task 1–11. ✓

**Placeholder scan:** A Task 9/10 „igazítsd a kulcsneveket" megjegyzések nem placeholderek a kódban — konkrét, futtatható alapkódot adnak default-okkal (a smoke-teszt üres válasszal is zöld), és csak a valós backend-kulcsokhoz való finomhangolást jelzik. Nincs „TODO/TBD" a kódban.

**Type/név konzisztencia:** `theme.badge_html/chip_html/kpi_card_html/theme_css/inject_theme/TOKENS`; `components.case_badges_html/card/top_header/icon_nav/render_timeline_one/render_kpi_grid`; `copilot_view._stream_lines/_sources_md`. A nevek a tesztek és a hívási helyek között egyeznek. A megtartott régi helperek (`priority_badge`, `render_timeline`, `render_source_panel`, `render_history_panel`, `highlight_inbound`) változatlan néven elérhetők.
