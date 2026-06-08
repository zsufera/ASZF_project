# Agentic válasz-szintézis + gazdag forrás-megjelenítés — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Az ügyintézői copilot mind a chat/telefon, mind az email úton koherens, LLM-szintetizált választ adjon inline `[Sn]` forrás-jelölőkkel és gazdag, lenyitható forrás-kártyákkal; LLM/forrás hiányában őszinte jelzés, nem idézet-dump.

**Architecture:** Új `synthesize_answer()` a `backend/draft.py`-ban egységesíti a válaszgenerálást (1 LLM-hívás); a `draft_node` minden csatornán ezt hívja. A `draft` objektum bővül (`sources[]`, `generation_mode`, `format`). A React egy új `InlineAnswer` komponenssel rendereli a `[Sn]` jelölőket kattintható chip-ekké, a `SourceCard` gazdaggá válik. A backend HTTP-szerződés nem változik.

**Tech Stack:** Python 3 / pytest (backend, LangGraph node), React 18 + TypeScript + Tailwind (frontend), Vite.

**Spec:** `docs/superpowers/specs/2026-06-08-agentic-answer-synthesis-design.md`

---

## Fájl-struktúra

**Backend (módosít):**
- `backend/draft.py` — ÚJ: `synthesize_answer()`, `_build_sources()`, `strip_source_markers()`, marker/prompt konstansok. A meglévő `build_draft` + helperek (`ensure_disclaimer`, `load_disclaimer`) változatlanok.
- `agent/nodes.py` — `draft_node` a `synthesize_answer()`-t hívja minden csatornán (a bedrótozott chat-ág törlése).
- `backend/case_service.py` — `approve_draft`: a kimenő ügyfél-szövegről `strip_source_markers`.

**Backend (tesztek):**
- `tests/test_synthesize_answer.py` — ÚJ.
- `tests/test_agent_graph.py` — kiegészítés (draft_node mindkét csatornán szintetizál).

**Frontend (módosít/létrehoz):**
- `frontend/src/lib/types.ts` — `SourceRef` + `AgentDraft` bővítés.
- `frontend/src/components/InlineAnswer.tsx` — ÚJ.
- `frontend/src/components/SourceCard.tsx` — gazdagítás.
- `frontend/src/screens/Copilot.tsx` — `InlineAnswer` + gazdag forrás-panel + insufficient banner.
- `frontend/src/screens/CaseWorkstation.tsx` — draft-előnézet `InlineAnswer` + insufficient banner + ref-alapú scroll.

---

## Task 1: Forrás-segédfüggvények és jelölő-tisztítás (`backend/draft.py`)

**Files:**
- Modify: `backend/draft.py` (új függvények a fájl tetejéhez, a meglévők alá)
- Test: `tests/test_synthesize_answer.py` (új)

- [ ] **Step 1: Write the failing test**

Create `tests/test_synthesize_answer.py`:

```python
from backend.draft import strip_source_markers, _build_sources


def test_strip_source_markers_removes_tokens_and_normalizes():
    text = "A felmondás 60 napos [S1] . A kedvezmény visszafizetése [S2] is releváns."
    assert strip_source_markers(text) == "A felmondás 60 napos. A kedvezmény visszafizetése is releváns."


def test_strip_source_markers_handles_empty():
    assert strip_source_markers("") == ""
    assert strip_source_markers(None) == ""


def test_build_sources_assigns_sequential_refs():
    policy_items = [
        {"chunk_id": "c1", "dok_cim": "ÁSZF", "dok_tipus": "ASZF", "paragrafus": "8.4",
         "oldalszam": 94, "idezet": "idézet1", "kozertheto_magyarazat": "magy1", "score": 0.8},
        {"chunk_id": "c2", "idezet": "idézet2"},
    ]
    sources = _build_sources(policy_items)
    assert [s["ref"] for s in sources] == ["S1", "S2"]
    assert sources[0]["dok_cim"] == "ÁSZF"
    assert sources[0]["magyarazat"] == "magy1"
    assert sources[0]["used"] is False
    assert sources[1]["chunk_id"] == "c2"


def test_build_sources_skips_items_without_chunk_id():
    sources = _build_sources([{"idezet": "x"}, {"chunk_id": "c1", "idezet": "y"}])
    assert [s["ref"] for s in sources] == ["S1"]
    assert sources[0]["chunk_id"] == "c1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_synthesize_answer.py -v`
Expected: FAIL with `ImportError: cannot import name 'strip_source_markers'`

- [ ] **Step 3: Write minimal implementation**

In `backend/draft.py`, add after the imports (after `from backend.llm import chat_json, llm_available`):

```python
import re

MARKER_RE = re.compile(r"\[S\d+\]")


def strip_source_markers(text: str | None) -> str:
    """Eltávolítja a [Sn] forrás-jelölőket és normalizálja a felesleges szóközöket."""
    cleaned = MARKER_RE.sub("", text or "")
    cleaned = re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _build_sources(policy_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """policy_items -> rendezett, ref-indexelt gazdag forrás-objektumok."""
    sources: list[dict[str, Any]] = []
    for item in policy_items:
        if not item.get("chunk_id"):
            continue
        sources.append({
            "ref": f"S{len(sources) + 1}",
            "chunk_id": item.get("chunk_id"),
            "dok_cim": item.get("dok_cim"),
            "dok_tipus": item.get("dok_tipus"),
            "paragrafus": item.get("paragrafus"),
            "oldalszam": item.get("oldalszam"),
            "idezet": item.get("idezet", ""),
            "magyarazat": item.get("kozertheto_magyarazat"),
            "score": item.get("score"),
            "used": False,
        })
    return sources
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_synthesize_answer.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/draft.py tests/test_synthesize_answer.py
git commit -m "feat: source-marker helpers for answer synthesis"
```

---

## Task 2: `synthesize_answer()` — LLM-szintézis + őszinte fallback (`backend/draft.py`)

**Files:**
- Modify: `backend/draft.py`
- Test: `tests/test_synthesize_answer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_synthesize_answer.py`:

```python
import backend.draft as draft
from config.settings import settings

_PMAP = {
    "policy_items": [
        {"chunk_id": "c1", "dok_cim": "ÁSZF", "dok_tipus": "ASZF", "paragrafus": "8.4",
         "oldalszam": 94, "idezet": "60 napos felmondási idő.", "kozertheto_magyarazat": "magy", "score": 0.9},
    ],
    "missing_mandatory": [],
}


def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")


def test_synthesize_llm_email_marks_used_sources(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "Válasz felmondás ügyben",
        "valasz": "A felmondás 60 napos határidővel lehetséges [S1].",
        "felhasznalt_forrasok": ["S1"],
        "elegtelen_fedezet": False,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "llm"
    assert result["format"] == "email"
    assert result["subject"] == "Válasz felmondás ügyben"
    assert "[S1]" in result["body_masked"]
    assert result["sources"][0]["used"] is True
    assert result["citations"] == ["c1"]


def test_synthesize_copilot_format(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "x", "valasz": "Beszédpont [S1].", "felhasznalt_forrasok": ["S1"], "elegtelen_fedezet": False,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="chat",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["format"] == "copilot"
    assert result["generation_mode"] == "llm"


def test_synthesize_strips_invalid_markers(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "x", "valasz": "Valós [S1] és kamu [S9] jelölő.",
        "felhasznalt_forrasok": ["S1", "S9"], "elegtelen_fedezet": False,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert "[S1]" in result["body_masked"]
    assert "[S9]" not in result["body_masked"]


def test_synthesize_insufficient_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "insufficient"
    assert "forrás" not in result["body_masked"].lower() or "fedezet" in result["body_masked"].lower()
    assert "(forrás:" not in result["body_masked"]
    assert len(result["sources"]) == 1  # megtalált forrás megjelenik


def test_synthesize_insufficient_without_sources(monkeypatch):
    _enable_llm(monkeypatch)
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map={"policy_items": []}, actions=[],
    )
    assert result["generation_mode"] == "insufficient"
    assert result["sources"] == []


def test_synthesize_insufficient_when_llm_flags_uncovered(monkeypatch):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(draft, "chat_json", lambda s, u: {
        "targy": "x", "valasz": "akármi", "felhasznalt_forrasok": [], "elegtelen_fedezet": True,
    })
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "insufficient"


def test_synthesize_insufficient_on_llm_exception(monkeypatch):
    _enable_llm(monkeypatch)
    def _boom(s, u):
        raise RuntimeError("api down")
    monkeypatch.setattr(draft, "chat_json", _boom)
    result = draft.synthesize_answer(
        case_id="c", category="felmondas", channel="email",
        output_mode="hitl", policy_map=_PMAP, actions=[],
    )
    assert result["generation_mode"] == "insufficient"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_synthesize_answer.py -v`
Expected: FAIL with `AttributeError: module 'backend.draft' has no attribute 'synthesize_answer'`

- [ ] **Step 3: Write minimal implementation**

In `backend/draft.py`, add at the end of the file:

```python
SYNTH_SYSTEM = (
    "Készíts az ügyintézőnek koherens, magyar nyelvű választ KIZÁRÓLAG a megadott ÁSZF-források alapján.\n"
    "Szabályok:\n"
    "- Minden tartalmi állítás mögé tedd a forrás jelölőjét szögletes zárójelben, pl. [S1]. Csak létező jelölőt használj.\n"
    "- Ha valamire nincs fedezet a forrásokban, NE találd ki.\n"
    "- Ha a források együtt sem elegendők érdemi válaszhoz, az elegtelen_fedezet mező legyen true.\n"
    "- A maszkolt PII-t (pl. [NÉV_1]) hagyd érintetlenül.\n"
    'Válasz JSON: {"targy": "...", "valasz": "... [S1] ...", '
    '"felhasznalt_forrasok": ["S1"], "elegtelen_fedezet": false}'
)

_EMAIL_INSTRUCTION = (
    "Formátum: hivatalos magyar ügyfél-válaszlevél (megszólítás, törzs, "
    "javasolt intézkedés, elköszönés)."
)
_COPILOT_INSTRUCTION = (
    "Formátum: tömör, az ügyintézőnek szóló beszédpont-összegzés "
    "(NEM közvetlen ügyfélnek címzett levél)."
)
_INSUFFICIENT_EMAIL = (
    "Nincs elegendő ÁSZF-fedezet automatikus válaszjavaslathoz. "
    "Emberi ellenőrzés és szükség esetén eszkaláció javasolt."
)
_INSUFFICIENT_COPILOT = (
    "Nincs elegendő ÁSZF-fedezet a kérdés megválaszolásához. "
    "Javasolt: emberi ellenőrzés / eszkaláció."
)


def _insufficient_result(fmt: str, category: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    subject = (
        f"Válaszjavaslat {category} ügyben" if fmt == "email" else f"Copilot jegyzet – {category}"
    )
    body = _INSUFFICIENT_COPILOT if fmt == "copilot" else _INSUFFICIENT_EMAIL
    return {
        "subject": subject,
        "body_masked": body,
        "sources": sources,
        "citations": [s["chunk_id"] for s in sources],
        "generation_mode": "insufficient",
        "format": fmt,
        "disclaimer_applied": False,
    }


def synthesize_answer(
    case_id: str,
    category: str,
    channel: str,
    output_mode: str,
    policy_map: dict[str, Any],
    actions: list[dict[str, Any]],
    disclaimer_text: str | None = None,
) -> dict[str, Any]:
    fmt = "copilot" if channel in {"chat", "phone"} else "email"
    sources = _build_sources(policy_map.get("policy_items", []))

    if not llm_available() or not sources:
        return _insufficient_result(fmt, category, sources)

    try:
        sources_block = "\n".join(
            f'- [{s["ref"]}] "{s["idezet"]}" '
            f'({s.get("dok_cim") or s.get("dok_tipus") or ""} §{s.get("paragrafus") or ""})'
            for s in sources
        )
        action_block = "\n".join(
            f'- {a.get("tipus")}: {a.get("indok", "")}' for a in actions if a.get("tipus")
        ) or "- (nincs)"
        instruction = _EMAIL_INSTRUCTION if fmt == "email" else _COPILOT_INSTRUCTION
        user = (
            f"{instruction}\n"
            f"Kategória: {category}\n"
            f"Kimeneti mód: {output_mode}\n"
            f"Források:\n{sources_block}\n"
            f"Javasolt intézkedés:\n{action_block}"
        )
        data = chat_json(SYNTH_SYSTEM, user)
        if data.get("elegtelen_fedezet"):
            return _insufficient_result(fmt, category, sources)
        body = str(data.get("valasz", "")).strip()
        if not body:
            return _insufficient_result(fmt, category, sources)

        valid_refs = {s["ref"] for s in sources}
        # Csak a ténylegesen létező [Sn] jelölők maradnak; az érvénytelent töröljük.
        body = re.sub(
            r"\[S(\d+)\]",
            lambda m: m.group(0) if f"S{m.group(1)}" in valid_refs else "",
            body,
        )
        used_refs = {r for r in (data.get("felhasznalt_forrasok") or []) if r in valid_refs}
        for s in sources:
            s["used"] = s["ref"] in used_refs or f'[{s["ref"]}]' in body

        subject = str(
            data.get("targy")
            or (f"Válaszjavaslat {category} ügyben" if fmt == "email" else f"Copilot jegyzet – {category}")
        )

        disclaimer_applied = False
        if fmt == "email":
            body, disclaimer_applied = ensure_disclaimer(body, output_mode)

        cited = [s["chunk_id"] for s in sources if s["used"]]
        return {
            "subject": subject,
            "body_masked": body,
            "sources": sources,
            "citations": cited or [s["chunk_id"] for s in sources],
            "generation_mode": "llm",
            "format": fmt,
            "disclaimer_applied": disclaimer_applied,
        }
    except Exception:
        return _insufficient_result(fmt, category, sources)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_synthesize_answer.py -v`
Expected: PASS (mind a ~11 teszt)

- [ ] **Step 5: Commit**

```bash
git add backend/draft.py tests/test_synthesize_answer.py
git commit -m "feat: synthesize_answer with inline citations and honest fallback"
```

---

## Task 3: `draft_node` egységesítése (`agent/nodes.py`)

**Files:**
- Modify: `agent/nodes.py:259-294` (`draft_node`), import sor (12)
- Test: `tests/test_agent_graph.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_agent_graph.py` (a meglévő importok mellé szükség szerint `import agent.nodes as nodes`):

```python
import agent.nodes as nodes


def test_draft_node_uses_synthesize_for_chat(monkeypatch):
    captured = {}

    def fake_synth(**kwargs):
        captured.update(kwargs)
        return {"subject": "s", "body_masked": "Válasz [S1].",
                "sources": [{"ref": "S1", "chunk_id": "c1", "used": True}],
                "citations": ["c1"], "generation_mode": "llm", "format": "copilot",
                "disclaimer_applied": False}

    monkeypatch.setattr(nodes, "synthesize_answer", fake_synth)
    state = {
        "case_id": "c", "channel": "chat",
        "classification": {"category": "felmondas"},
        "policy_map": {"policy_items": [{"chunk_id": "c1"}]},
        "actions": [], "timeline": [],
    }
    out = nodes.draft_node(state)
    assert captured["channel"] == "chat"
    assert out["draft"]["format"] == "copilot"
    # a régi bedrótozott prefix már NEM jelenik meg
    assert not out["draft"]["body_masked"].startswith("Beszédpontok:")


def test_draft_node_uses_synthesize_for_email(monkeypatch):
    def fake_synth(**kwargs):
        return {"subject": "s", "body_masked": "Levél [S1].",
                "sources": [], "citations": [], "generation_mode": "llm",
                "format": "email", "disclaimer_applied": False}

    monkeypatch.setattr(nodes, "synthesize_answer", fake_synth)
    state = {
        "case_id": "c", "channel": "email",
        "classification": {"category": "szamlazas"},
        "policy_map": {"policy_items": []},
        "actions": [], "timeline": [],
    }
    out = nodes.draft_node(state)
    assert out["draft"]["format"] == "email"
    assert out["timeline"][-1]["output"]["generation_mode"] == "llm"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agent_graph.py::test_draft_node_uses_synthesize_for_chat -v`
Expected: FAIL (`AttributeError: ... has no attribute 'synthesize_answer'` a `nodes` modulban, mert még nincs importálva/használva)

- [ ] **Step 3: Write minimal implementation**

In `agent/nodes.py`, módosítsd az importot (12. sor környéke):

```python
from backend.draft import build_draft, synthesize_answer
```

Cseréld le a teljes `draft_node` függvényt (jelenleg 259–294) erre:

```python
def draft_node(state: AgentState) -> AgentState:
    channel = state.get("channel", "email")
    classification = state.get("classification", {})
    category = classification.get("category", "egyeb")
    policy_map = state.get("policy_map", {})
    actions = state.get("actions", [])
    output_mode = state.get("output_mode", "hitl")

    result = synthesize_answer(
        case_id=state["case_id"],
        category=category,
        channel=channel,
        output_mode=output_mode,
        policy_map=policy_map,
        actions=actions,
    )

    return {
        "draft": result,
        "timeline": _append_timeline(state, "draft", {
            "format": result.get("format"),
            "citation_count": len(result.get("citations", [])),
            "source_count": len(result.get("sources", [])),
            "generation_mode": result.get("generation_mode"),
        }),
    }
```

> A `build_draft` import megmarad (más helyen még hivatkozhatják / tesztek fedik); ha a linter unused-importot jelez, a `build_draft`-ot hagyd benn explicit kommenttel: `# build_draft: legacy letter builder, tesztek fedik`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_agent_graph.py -v`
Expected: PASS (az új 2 teszt + a meglévők zöldek)

- [ ] **Step 5: Run the full backend suite to catch regressions**

Run: `python -m pytest tests/ -q`
Expected: minden zöld (a `build_draft` saját tesztjei is, mert a függvény változatlan)

- [ ] **Step 6: Commit**

```bash
git add agent/nodes.py tests/test_agent_graph.py
git commit -m "refactor: draft_node uses unified synthesize_answer for all channels"
```

---

## Task 4: Jelölő-tisztítás jóváhagyáskor (`backend/case_service.py`)

**Files:**
- Modify: `backend/case_service.py` (import + `approve_draft` 611–612 körül)
- Test: `tests/test_synthesize_answer.py` (vagy meglévő case-service teszt; itt egységként)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_synthesize_answer.py`:

```python
def test_approve_strips_markers_from_unmasked_body(monkeypatch):
    import backend.case_service as cs

    # unmask_text legyen azonosság (nincs DB-függés a teszthez)
    monkeypatch.setattr(cs, "unmask_text", lambda code, text: text)
    cleaned = cs._clean_outbound_text("A felmondás 60 napos [S1] határidővel.")
    assert "[S1]" not in cleaned
    assert cleaned == "A felmondás 60 napos határidővel."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_synthesize_answer.py::test_approve_strips_markers_from_unmasked_body -v`
Expected: FAIL (`AttributeError: module 'backend.case_service' has no attribute '_clean_outbound_text'`)

- [ ] **Step 3: Write minimal implementation**

In `backend/case_service.py`, add the import near the top (a `draft` importok közé):

```python
from backend.draft import strip_source_markers
```

Add a small helper near the other module-level helpers:

```python
def _clean_outbound_text(text: str) -> str:
    """Az ügyfélhez kimenő szövegből eltávolítja a belső [Sn] forrás-jelölőket."""
    return strip_source_markers(text)
```

In `approve_draft`, change lines 611–612 from:

```python
    subject_unmasked = unmask_text(case_code, subject_masked or "")
    body_unmasked = unmask_text(case_code, body_masked or "")
```

to:

```python
    subject_unmasked = _clean_outbound_text(unmask_text(case_code, subject_masked or ""))
    body_unmasked = _clean_outbound_text(unmask_text(case_code, body_masked or ""))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_synthesize_answer.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: minden zöld

- [ ] **Step 6: Commit**

```bash
git add backend/case_service.py tests/test_synthesize_answer.py
git commit -m "feat: strip source markers from customer-facing text on approval"
```

---

## Task 5: Frontend típusok (`frontend/src/lib/types.ts`)

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add the SourceRef type and extend AgentState.draft**

A `frontend/src/lib/types.ts`-ben, a `ChunkItem` interfész alá add:

```typescript
export interface SourceRef {
  ref: string;            // "S1", "S2", ...
  chunk_id: string;
  dok_cim?: string;
  dok_tipus?: string;
  paragrafus?: string;
  oldalszam?: number;
  idezet: string;
  magyarazat?: string;
  score?: number;
  used: boolean;
}

export type GenerationMode = "llm" | "insufficient";
```

Az `AgentState` interfészben a `draft` mezőt bővítsd:

```typescript
  draft: {
    subject: string;
    body_masked: string;
    citations: string[];
    sources?: SourceRef[];
    generation_mode?: GenerationMode;
    format?: "email" | "copilot";
  };
```

- [ ] **Step 2: Verify types compile**

Run: `cd frontend; npx tsc --noEmit`
Expected: nincs kimenet (tiszta)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat(ui): SourceRef type and draft synthesis fields"
```

---

## Task 6: `InlineAnswer` komponens (`frontend/src/components/InlineAnswer.tsx`)

**Files:**
- Create: `frontend/src/components/InlineAnswer.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { Fragment } from "react";
import type { SourceRef } from "../lib/types";

interface InlineAnswerProps {
  body: string;
  sources?: SourceRef[];
  onCite?: (ref: string) => void;
}

const MARKER = /\[S\d+\]/g;

/**
 * A body szövegben a [Sn] jelölőket kattintható türkiz chip-ekké alakítja.
 * Ismeretlen ref (nincs a sources között) sima szövegként jelenik meg.
 */
export function InlineAnswer({ body, sources, onCite }: InlineAnswerProps) {
  const validRefs = new Set((sources ?? []).map((s) => s.ref));
  const parts = body.split(MARKER);
  const markers = body.match(MARKER) ?? [];

  return (
    <div className="text-[12px] leading-relaxed whitespace-pre-wrap">
      {parts.map((part, i) => {
        const marker = markers[i]; // a part UTÁN következő jelölő
        const ref = marker ? marker.slice(1, -1) : null;
        return (
          <Fragment key={i}>
            {part}
            {ref && validRefs.has(ref) ? (
              <button
                onClick={() => onCite?.(ref)}
                className="inline-flex items-center align-baseline mx-0.5 text-[9px] font-bold bg-one-turq-l text-one-turq-d border border-one-turq rounded-full px-1.5 py-0.5 hover:bg-one-turq hover:text-[#04201f] transition-colors"
                aria-label={`Forrás ${ref}`}
              >
                {ref}
              </button>
            ) : ref ? (
              // ismeretlen ref: ne jelenjen meg nyersen
              <span />
            ) : null}
          </Fragment>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend; npx tsc --noEmit`
Expected: tiszta

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/InlineAnswer.tsx
git commit -m "feat(ui): InlineAnswer renders [Sn] markers as clickable chips"
```

---

## Task 7: `SourceCard` gazdagítás (`frontend/src/components/SourceCard.tsx`)

**Files:**
- Modify: `frontend/src/components/SourceCard.tsx`

- [ ] **Step 1: Add a SourceRef-based rich card variant**

Cseréld le a `SourceCard.tsx` teljes tartalmát erre (a meglévő `ChunkItem`-alapú aláírás megmarad a visszafelé-kompatibilitásért, plusz egy új `RichSourceCard`):

```tsx
import { useState } from "react";
import type { ChunkItem, SourceRef } from "../lib/types";

interface SourceCardProps {
  chunk: ChunkItem;
  id?: string;
  onJump?: () => void;
}

export function SourceCard({ chunk, id, onJump }: SourceCardProps) {
  const [showExplain, setShowExplain] = useState(false);
  const quote = chunk.quote ?? chunk.idezet ?? "";

  return (
    <div
      id={id}
      className="border-l-2 border-one-turq bg-[#FbFdfd] rounded-r-md px-3 py-2 mb-2 text-[11px] transition-all duration-150"
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold text-one-turq-d">§ {chunk.paragrafus} · {chunk.dok_tipus}</span>
        {onJump && (
          <button onClick={onJump} className="text-one-turq-d hover:underline ml-2" aria-label="Ugrás a teljes szakaszra">⤴</button>
        )}
      </div>
      {quote && <p className="italic text-[#33403f] mb-1">„{quote}"</p>}
      {chunk.kozertheto_magyarazat && (
        <>
          <button
            onClick={() => setShowExplain((v) => !v)}
            className="text-[9px] text-one-turq-d border border-one-turq rounded-full px-2 py-0.5 hover:bg-one-turq-l transition-colors"
            aria-expanded={showExplain}
          >
            {showExplain ? "Elrejt" : "Közérthető magyarázat"}
          </button>
          {showExplain && <p className="mt-2 text-one-grey text-[10px] animate-fade-in">{chunk.kozertheto_magyarazat}</p>}
        </>
      )}
    </div>
  );
}

function relevanceLabel(score?: number): string | null {
  if (score === undefined || score === null) return null;
  if (score >= 0.75) return "magas";
  if (score >= 0.4) return "közepes";
  return "alacsony";
}

interface RichSourceCardProps {
  source: SourceRef;
  id?: string;
}

/** Gazdag, lenyitható forrás-kártya a SourceRef adatokból. */
export function RichSourceCard({ source, id }: RichSourceCardProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const rel = relevanceLabel(source.score);

  const copyId = () => {
    navigator.clipboard?.writeText(source.chunk_id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }).catch(() => {});
  };

  return (
    <div
      id={id}
      className={`border-l-2 rounded-r-md px-3 py-2 mb-2 text-[11px] transition-all duration-150 ${source.used ? "border-one-turq bg-[#FbFdfd]" : "border-one-line bg-white opacity-70"}`}
    >
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center justify-between text-left" aria-expanded={open}>
        <span className="flex items-center gap-2 min-w-0">
          <span className="text-[9px] font-bold bg-one-turq-l text-one-turq-d border border-one-turq rounded-full px-1.5 py-0.5 flex-none">{source.ref}</span>
          <span className="font-semibold text-one-ink truncate">{source.dok_cim ?? source.dok_tipus ?? "Forrás"}{source.paragrafus ? ` · §${source.paragrafus}` : ""}</span>
        </span>
        <span className="flex items-center gap-1 flex-none ml-2">
          {rel && <span className="text-[9px] text-one-grey">{rel}</span>}
          <span className="text-one-grey">{open ? "▾" : "▸"}</span>
        </span>
      </button>

      {open && (
        <div className="mt-2 animate-fade-in">
          <div className="flex flex-wrap gap-2 text-[9px] text-one-grey mb-1">
            {source.dok_tipus && <span>{source.dok_tipus}</span>}
            {source.oldalszam !== undefined && <span>· {source.oldalszam}. oldal</span>}
          </div>
          {source.idezet && <p className="italic text-[#33403f] mb-1">„{source.idezet}"</p>}
          {source.magyarazat && <p className="text-one-grey text-[10px] mb-1">{source.magyarazat}</p>}
          <button onClick={copyId} className="text-[9px] text-one-turq-d hover:underline" aria-label="chunk_id másolása">
            {copied ? "✓ másolva" : `id: ${source.chunk_id}`}
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend; npx tsc --noEmit`
Expected: tiszta

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SourceCard.tsx
git commit -m "feat(ui): RichSourceCard collapsible source detail"
```

---

## Task 8: Copilot bekötése (`frontend/src/screens/Copilot.tsx`)

**Files:**
- Modify: `frontend/src/screens/Copilot.tsx`

- [ ] **Step 1: Capture sources + generation_mode from agentRun and render**

A `Copilot.tsx`-ben a `Message` interfészt bővítsd, és a `sendMessage` a `draft`-ból olvassa a `sources`-t és a `generation_mode`-ot. Konkrétan:

A `Message` interfész:

```tsx
import type { SourceRef } from "../lib/types";
import { InlineAnswer } from "../components/InlineAnswer";
import { RichSourceCard } from "../components/SourceCard";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
  generationMode?: "llm" | "insufficient";
}
```

A `sendMessage` try-ágában a válasz feldolgozása:

```tsx
      const res = await api.agentRun({
        case_id: sessionCaseId,
        channel: "chat",
        input_text: text,
        output_mode: outputMode,
      }) as { draft?: { body_masked?: string; sources?: SourceRef[]; generation_mode?: "llm" | "insufficient" } };

      const body = res.draft?.body_masked ?? "Nincs válasz.";
      const sources = res.draft?.sources ?? [];
      const generationMode = res.draft?.generation_mode;
      setLastAssistantFull(body);
      setStreamTrigger((n) => n + 1);
      setMessages((prev) => [...prev, { role: "assistant", content: body, sources, generationMode }]);
```

- [ ] **Step 2: Render the assistant turn with InlineAnswer + sources panel**

A `messages.map(...)` asszisztens-ágában a sima `<ChatTurn>` helyett (csak az utolsó, kész asszisztens-üzenetnél) használj `InlineAnswer`-t. A legegyszerűbb: tartsd meg a `ChatTurn`-t a user-buborékhoz és a streameléshez, de a kész asszisztens-választ rendereld egy bővített buborékban. Cseréld le a `messages.map` blokkot erre:

```tsx
              {messages.map((m, i) => {
                const isLastAssistant = m.role === "assistant" && i === messages.length - 1;
                const streaming = isLastAssistant && loading;
                if (m.role === "assistant" && !streaming) {
                  return (
                    <div key={i} className="flex gap-2 mb-3 animate-fade-up">
                      <div className="w-7 h-7 rounded-full bg-one-turq-l flex items-center justify-center text-[11px] flex-none" aria-label="Copilot">◎</div>
                      <div className="rounded-xl px-3 py-2 max-w-[80%] bg-one-turq-l text-one-ink">
                        {m.generationMode === "insufficient" && (
                          <div className="mb-2 bg-status-esc-bg border border-status-esc-fg rounded-md px-2 py-1 text-[10px] text-status-esc-fg">
                            ⚠ Nincs elég ÁSZF-fedezet — emberi ellenőrzés / eszkaláció javasolt.
                          </div>
                        )}
                        <InlineAnswer body={m.content} sources={m.sources} onCite={(ref) => {
                          document.getElementById(`copilot-src-${ref}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                        }} />
                      </div>
                    </div>
                  );
                }
                return (
                  <ChatTurn
                    key={i}
                    role={m.role}
                    content={streaming ? streamedText : m.content}
                  />
                );
              })}
```

- [ ] **Step 3: Replace the right-hand sources panel with RichSourceCard**

A jobb oldali panelben a „Hivatkozott források" blokkot cseréld erre (a `messages.some(... m.sources ...)` feltételt a `SourceRef[]`-hez igazítva):

```tsx
            {(() => {
              const lastWithSources = [...messages].reverse().find((m) => m.sources && m.sources.length > 0);
              if (!lastWithSources?.sources?.length) return null;
              return (
                <div className="bg-one-surface border border-one-line rounded-one shadow-card p-3">
                  <h3 className="text-[10px] uppercase text-one-grey tracking-wider mb-2">📚 Hivatkozott források</h3>
                  {lastWithSources.sources.map((s) => (
                    <RichSourceCard key={s.ref} source={s} id={`copilot-src-${s.ref}`} />
                  ))}
                </div>
              );
            })()}
```

- [ ] **Step 4: Verify it compiles**

Run: `cd frontend; npx tsc --noEmit`
Expected: tiszta (ha a régi `messages.some` / `ChatTurn sources` hivatkozás maradt, töröld; a `SourceChip` import a ChatTurn-ben maradhat)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/Copilot.tsx
git commit -m "feat(ui): copilot renders synthesized answer with inline citations and rich sources"
```

---

## Task 9: Ügy-munkaállomás bekötése (`frontend/src/screens/CaseWorkstation.tsx`)

**Files:**
- Modify: `frontend/src/screens/CaseWorkstation.tsx`

- [ ] **Step 1: Use RichSourceCard + InlineAnswer + insufficient banner**

A `CaseWorkstation.tsx`-ben:

1. Importok:

```tsx
import { InlineAnswer } from "../components/InlineAnswer";
import { RichSourceCard } from "../components/SourceCard";
```

2. A draft/források kiolvasásánál (a `const chunks = ...` környékén) add hozzá:

```tsx
  const sources = caseData.agent_state?.draft?.sources ?? [];
  const generationMode = caseData.agent_state?.draft?.generation_mode;
```

3. A **Források** kártyában (`<Card title="📚 Források">`) ha van `sources`, azt rendereld gazdag kártyaként; egyébként maradjon a meglévő `chunks` alapú `SourceCard` (visszafelé-kompatibilitás):

```tsx
          <Card title="📚 Források">
            {sources.length > 0 ? (
              sources.map((s) => (
                <div key={s.ref} ref={(el) => { sourceRefs.current[s.ref] = el; }}>
                  <RichSourceCard source={s} id={`source-${s.ref}`} />
                </div>
              ))
            ) : chunks.length === 0 ? (
              <p className="text-one-grey text-[11px]">Nincs forrás.</p>
            ) : (
              chunks.map((c) => (
                <div key={c.chunk_id} ref={(el) => { sourceRefs.current[c.chunk_id] = el; }}>
                  <SourceCard chunk={c} id={`source-${c.chunk_id}`} />
                </div>
              ))
            )}
          </Card>
```

4. A **Draft** kártyában, az `escalation` figyelmeztetés mellé add az insufficient bannert (a `<DraftEditor .../>` fölé), és a draft body előnézetét egészítsd ki: a `DraftEditor` szerkesztő marad, de fölé tegyél egy „fedezet-előnézetet" `InlineAnswer`-rel, ami a `ref`-re kattintva a forrás-kártyára görget:

```tsx
            {generationMode === "insufficient" && (
              <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
                ⚠ Nincs elég ÁSZF-fedezet automatikus válaszhoz — emberi ellenőrzés / eszkaláció javasolt.
              </div>
            )}
            {hasTimeline && draft.body_masked && (
              <div className="mb-3 bg-[#FbFdfd] border border-one-line rounded-md p-2">
                <div className="text-[9px] uppercase text-one-grey tracking-wider mb-1">Fedezet-előnézet (kattintható forrás-jelölők)</div>
                <InlineAnswer
                  body={draft.body_masked}
                  sources={sources}
                  onCite={(ref) => {
                    const el = sourceRefs.current[ref];
                    if (el) {
                      el.scrollIntoView({ behavior: "smooth", block: "center" });
                      el.classList.add("ring-2", "ring-one-turq");
                      setTimeout(() => el.classList.remove("ring-2", "ring-one-turq"), 1500);
                    }
                  }}
                />
              </div>
            )}
```

> A `sourceRefs` mostantól `ref`-kulccsal (S1…) is tárol; ez nem ütközik a régi `chunk_id`-kulcsokkal. A `handleCitationClick` (régi chunk_id-alapú) maradhat a `DraftEditor` citation-jaihoz.

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend; npx tsc --noEmit`
Expected: tiszta

- [ ] **Step 3: Production build**

Run: `cd frontend; npm run build`
Expected: `built in ...` hiba nélkül

- [ ] **Step 4: Commit**

```bash
git add frontend/src/screens/CaseWorkstation.tsx
git commit -m "feat(ui): case workstation rich sources + inline citation preview + insufficient banner"
```

---

## Task 10: Teljes verifikáció + kézi füstpróba

**Files:** (nincs új fájl)

- [ ] **Step 1: Backend suite zöld**

Run: `python -m pytest tests/ -q`
Expected: minden teszt zöld

- [ ] **Step 2: Frontend típus + build**

Run: `cd frontend; npx tsc --noEmit; npm run build`
Expected: tiszta tsc, sikeres build

- [ ] **Step 3: Kézi füstpróba (backend + dev szerver fut)**

Háttér: `uvicorn backend.main:app --reload` (8000) és `cd frontend; npm run dev` (5173).
Ellenőrzendő:
1. Copilot chat → küldj „Fel szeretném mondani a vezetékes szerződésemet" üzenetet → **koherens, összefüggő válasz** `[S1]…` chip-ekkel; a chip-re kattintva a jobb oldali forrás-kártya kiemelődik; a kártya lenyitható (idézet, paragrafus, oldal, magyarázat, másolható id).
2. Egy email ügy megnyitása → agent indítása → a draftban koherens levél, fölötte „Fedezet-előnézet" kattintható jelölőkkel; bal oldalon gazdag forrás-kártyák.
3. Ha az LLM nem elérhető (pl. `LLM_ENABLED=false` ideiglenesen) → **insufficient banner**, nincs idézet-dump, de a megtalált források láthatók.

- [ ] **Step 4: Final commit (ha maradt nyitva bármi)**

```bash
git add -A
git commit -m "chore: agentic answer synthesis verification" --allow-empty
```

---

## Önellenőrzés (spec-lefedettség)

- Inline `[Sn]` jelölők + gazdag panel (döntés 1) → Task 6, 7, 8, 9 ✓
- Gazdag, lenyitható forrás-kártya (döntés 2) → Task 7 ✓
- Őszinte fallback, nincs idézet-dump (döntés 3) → Task 2 (`_insufficient_result`), tesztek ✓
- Egységesített synthesize_answer, 1 LLM-hívás (megközelítés A) → Task 2, 3 ✓
- Email-levél tisztul approve-nál → Task 4 ✓
- Backend HTTP-szerződés változatlan → nincs endpoint-módosítás ✓
- Tesztelés (backend pytest + frontend tsc/build) → Task 2, 3, 4, 10 ✓
