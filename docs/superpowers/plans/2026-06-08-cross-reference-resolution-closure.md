# Cross-doc referencia-feloldás + reference-closure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A visszakeresett §-ok által hivatkozott szakaszokat (lokális ÉS más dokumentumban) determinisztikusan behúzni a retrieval-eredménybe (1-hop, max +5), a feloldhatatlan hivatkozást pedig completeness-jelként visszaadni.

**Architecture:** Az `extract_references` (parse) strukturált hivatkozásokat (`raw`/`doc_hint`/`paragraph`) tölt a `chunks.jsonl` `cross_refs` mezőjébe. Egy új, tiszta `backend/reference_resolution.py` modul felépíti a dok-név- és paragrafus-indexeket, felold egy hivatkozást, és kiszámítja a closure-t. A `retrieve()` a régi `resolve_cross_refs` helyett ezt hívja. A meglévő `chunks.jsonl`-t egy backfill CLI dúsítja, majd Qdrant re-index.

**Tech Stack:** Python 3 / pytest. Hermetikus tesztek (re-index nélkül). Windows: `.venv/Scripts/python.exe -m pytest`, nincs `&&`.

**Spec:** `docs/superpowers/specs/2026-06-08-cross-reference-resolution-closure-design.md`

---

## Fájl-struktúra
- `preprocessing/parse.py` — MÓDOSÍT: `extract_cross_refs` → `extract_references` (strukturált); `Chunk.cross_refs` típus; a hívási hely (`:212`).
- `backend/reference_resolution.py` — ÚJ: normalizálók, indexek, `resolve_reference`, `reference_closure`.
- `backend/retrieval.py` — MÓDOSÍT: a `resolve_cross_refs` helyett `reference_closure`; `unresolved_refs` a válaszba.
- `preprocessing/enrich_cross_refs.py` — ÚJ CLI: a meglévő `chunks.jsonl` backfillje.
- Tesztek: `tests/test_extract_references.py` (ÚJ), `tests/test_reference_resolution.py` (ÚJ), `tests/test_retrieval.py` (MÓDOSÍT).

---

## Task 1: `extract_references` strukturált hivatkozás-kinyerés (`preprocessing/parse.py`)

**Files:**
- Modify: `preprocessing/parse.py`
- Test: `tests/test_extract_references.py` (új)

- [ ] **Step 1: Failing test** — `tests/test_extract_references.py`:

```python
from preprocessing.parse import extract_references


def test_extract_local_paragraph_reference():
    refs = extract_references("A 5.6 pont szerint további szabályok érvényesek.")
    assert {"raw": "5.6 pont", "doc_hint": None, "paragraph": "5.6"} in refs


def test_extract_cross_doc_reference_with_paragraph():
    refs = extract_references("Lásd a 2/B. számú melléklet 4.1.4 pont rendelkezéseit.")
    hit = [r for r in refs if r["doc_hint"]]
    assert hit and "melléklet" in hit[0]["doc_hint"].lower()
    assert hit[0]["paragraph"] == "4.1.4"


def test_extract_cross_doc_reference_without_paragraph():
    refs = extract_references("a 3. számú melléklete szerint")
    assert any(r["doc_hint"] and r["paragraph"] is None and "3" in r["doc_hint"] for r in refs)


def test_extract_dedups_and_skips_garbage():
    refs = extract_references("5.6 pont, majd ismét 5.6 pont. li. \nPont")
    paras = [r["paragraph"] for r in refs]
    assert paras.count("5.6") == 1


def test_extract_returns_empty_on_plain_text():
    assert extract_references("Ez egy sima mondat szám nélkül.") == []
```

- [ ] **Step 2: Run, expect FAIL**

Run: `.venv/Scripts/python.exe -m pytest tests/test_extract_references.py -v`
Expected: ImportError (`extract_references` nincs).

- [ ] **Step 3: Implement** — `preprocessing/parse.py`-ban a `CROSS_REF_PATTERN` definíció UTÁN add hozzá:

```python
DOC_REF_PATTERN = re.compile(
    r"(?i)(?P<doc>\d+\s*[ab]?(?:/[ab])?\.?\s*sz[áa]m[úu]?\s*(?:mell[ée]klet|f[üu]ggel[ée]k))"
    r"(?:e?\s*(?P<para>\d+(?:\.\d+){0,4})\s*(?:pont|bekezd[ée]s))?"
)
LOCAL_REF_PATTERN = re.compile(
    r"(?i)(?P<p1>\d+(?:\.\d+){1,4})\s*(?:pont|bekezd[ée]s)|(?P<p2>\d+)\s*§|"
    r"(?P<rom>[IVXLCDM]+)\.\s*(?:fejezet|pont)"
)
```

majd cseréld le az `extract_cross_refs` függvényt erre:

```python
def extract_references(text: str) -> list[dict]:
    """Strukturált hivatkozások a szövegből: lokális §/pont és kereszt-dok melléklet/függelék.

    Visszatérés elemei: {"raw": str, "doc_hint": str|None, "paragraph": str|None}.
    A doc_hint None, ha a hivatkozás a saját dokumentumra mutat.
    """
    refs: list[dict] = []
    seen: set[tuple] = set()

    def _add(doc_hint: str | None, paragraph: str | None, raw: str) -> None:
        key = (doc_hint, paragraph)
        if key in seen or (doc_hint is None and paragraph is None):
            return
        seen.add(key)
        refs.append({"raw": " ".join(raw.split()), "doc_hint": doc_hint, "paragraph": paragraph})

    for m in DOC_REF_PATTERN.finditer(text):
        doc = " ".join(m.group("doc").split())
        _add(doc, m.group("para"), m.group(0))
    for m in LOCAL_REF_PATTERN.finditer(text):
        paragraph = m.group("p1") or m.group("p2")
        if paragraph:
            _add(None, paragraph, m.group(0))
    return refs


# Visszafelé-kompatibilis alias (régi hívók / smoke):
def extract_cross_refs(text: str) -> list[dict]:
    return extract_references(text)
```

Frissítsd a `Chunk` dataclass mezőjét (`:47`): `cross_refs: list[str]` → `cross_refs: list[dict]`. A `parse_documents` hívási helyén (`:212`) `cross_refs=extract_cross_refs(section_text)` maradhat (az alias miatt) — vagy cseréld `extract_references`-re.

> Megjegyzés: a bare „Díjszabás"/„ESzSzF" (paragrafus nélküli, dok-szintű) hivatkozást **szándékosan nem** nyerjük ki — túl zajos és a feloldás úgyis `None` lenne (spec §7).

- [ ] **Step 4: Run, expect PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_extract_references.py -v`
Expected: 5 zöld. (Ha egy regex-csoport nem illeszkedik pontosan, igazítsd a mintát úgy, hogy a tesztek átmenjenek.)

- [ ] **Step 5: Commit**

```
git add preprocessing/parse.py tests/test_extract_references.py
git commit -m "feat: structured reference extraction (local + cross-doc) in parse"
```

---

## Task 2: Normalizálók + indexek + `resolve_reference` (`backend/reference_resolution.py`)

**Files:**
- Create: `backend/reference_resolution.py`
- Test: `tests/test_reference_resolution.py` (új)

- [ ] **Step 1: Failing test** — `tests/test_reference_resolution.py`:

```python
from backend.reference_resolution import (
    normalize_paragraph, build_doc_name_index, build_paragraph_index, resolve_reference,
)

CHUNKS = [
    {"chunk_id": "one_2a_p1", "doc_id": "doc_2a", "szolgaltato": "ONE", "paragrafus_szam": "4.1.4",
     "source_file": "data/raw_pdfs/ASZF_2A_mobil_melleklet_hatalyos_20260605.pdf", "text": "x"},
    {"chunk_id": "one_torzs_p1", "doc_id": "doc_torzs", "szolgaltato": "ONE", "paragrafus_szam": "5.5",
     "source_file": "data/raw_pdfs/ASZF_0_torzs_hatalyos_20260605.pdf", "text": "y"},
    {"chunk_id": "inv_1_p1", "doc_id": "doc_inv1", "szolgaltato": "Invitech", "paragrafus_szam": "1.1",
     "source_file": "data/raw_pdfs/InvitechASZF_1_sz_melleklet20260101.pdf", "text": "z"},
]


def test_normalize_paragraph_extracts_number():
    assert normalize_paragraph("5.5.1 pont") == "5.5.1"
    assert normalize_paragraph(None) == ""


def test_doc_name_index_maps_melleklet_per_provider():
    idx = build_doc_name_index(CHUNKS)
    assert idx[("ONE", "2a melleklet")] == "doc_2a"
    assert idx[("ONE", "2 melleklet")] == "doc_2a"
    assert idx[("Invitech", "1 melleklet")] == "doc_inv1"


def test_resolve_cross_doc_reference():
    src = CHUNKS[1]  # ONE törzs chunk
    ref = {"raw": "2/A. számú melléklet 4.1.4 pont", "doc_hint": "2/A. számú melléklet", "paragraph": "4.1.4"}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    hit = resolve_reference(ref, src, di, pi)
    assert hit is not None and hit["chunk_id"] == "one_2a_p1"


def test_resolve_local_reference_prefix_match():
    src = CHUNKS[0]
    ref = {"raw": "5.5 pont", "doc_hint": None, "paragraph": "5.5"}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    # lokális hivatkozás a forrás dokumentumában (doc_2a) — ott nincs 5.5 → None
    assert resolve_reference(ref, src, di, pi) is None
    # de a törzs chunkból (doc_torzs) feloldódik a saját 5.5-e
    assert resolve_reference(ref, CHUNKS[1], di, pi)["chunk_id"] == "one_torzs_p1"


def test_resolve_returns_none_without_paragraph():
    src = CHUNKS[1]
    ref = {"raw": "3. számú melléklet", "doc_hint": "3. számú melléklet", "paragraph": None}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    assert resolve_reference(ref, src, di, pi) is None


def test_resolve_does_not_cross_provider():
    src = CHUNKS[1]  # ONE
    ref = {"raw": "1. számú melléklet 1.1 pont", "doc_hint": "1. számú melléklet", "paragraph": "1.1"}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    # ONE-nál nincs "1 melleklet" → nem oldja fel az Invitech dokumentumát
    assert resolve_reference(ref, src, di, pi) is None
```

- [ ] **Step 2: Run, expect FAIL**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reference_resolution.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement** — `backend/reference_resolution.py`:

```python
from __future__ import annotations

import re
from typing import Any

from preprocessing.index import fold_text

_PARAGRAPH_NUMBER = re.compile(r"\d+(?:\.\d+){0,4}")
# fájlnévből: "...2a_mobil_melleklet...", "..._3_melleklet...", "...1_sz_melleklet..."
_MELLEKLET_IN_FILENAME = re.compile(r"(\d+)\s*([ab]?)[a-z0-9_]*?mellekl")
# hint-ből: "2/A. számú melléklet", "3. számú melléklet"
_MELLEKLET_IN_HINT = re.compile(r"(\d+)\s*([ab]?)(?:/([ab]))?\.?\s*sz[áa]m[úu]?\s*mellekl")


def normalize_paragraph(value: str | None) -> str:
    if not value:
        return ""
    match = _PARAGRAPH_NUMBER.search(str(value))
    return match.group(0) if match else fold_text(str(value))


def _melleklet_keys(num: str, letter: str) -> set[str]:
    keys = {f"{num} melleklet"}
    if letter:
        keys |= {f"{num}{letter} melleklet", f"{num}/{letter} melleklet"}
    return keys


def _doc_keys_from_filename(source_file: str) -> set[str]:
    base = fold_text(str(source_file).replace("\\", "/").rsplit("/", 1)[-1])
    match = _MELLEKLET_IN_FILENAME.search(base)
    if not match:
        return set()
    return _melleklet_keys(match.group(1), match.group(2))


def _doc_keys_from_hint(doc_hint: str) -> set[str]:
    match = _MELLEKLET_IN_HINT.search(fold_text(doc_hint))
    if not match:
        return set()
    letter = match.group(2) or match.group(3) or ""
    return _melleklet_keys(match.group(1), letter)


def build_doc_name_index(chunks: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    """(szolgaltato, normalizált dok-név) -> doc_id. Kétértelmű kulcs (ütköző doc_id) eldobva."""
    index: dict[tuple[str, str], str] = {}
    ambiguous: set[tuple[str, str]] = set()
    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        szolg = chunk.get("szolgaltato") or ""
        if not doc_id:
            continue
        for key in _doc_keys_from_filename(chunk.get("source_file") or ""):
            k = (szolg, key)
            if k in ambiguous:
                continue
            existing = index.get(k)
            if existing is not None and existing != doc_id:
                del index[k]
                ambiguous.add(k)
            else:
                index[k] = doc_id
    return index


def build_paragraph_index(chunks: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """(doc_id, normalizált paragrafus) -> chunk (első nyer)."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for chunk in chunks:
        doc_id = chunk.get("doc_id")
        paragraph = normalize_paragraph(chunk.get("paragrafus_szam") or chunk.get("paragrafus"))
        if not doc_id or not paragraph:
            continue
        index.setdefault((doc_id, paragraph), chunk)
    return index


def resolve_reference(
    ref: dict[str, Any],
    source_chunk: dict[str, Any],
    doc_name_index: dict[tuple[str, str], str],
    paragraph_index: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any] | None:
    paragraph = normalize_paragraph(ref.get("paragraph"))
    if not paragraph:
        return None  # dok-szintű hivatkozás (paragrafus nélkül) — szándékosan nem oldjuk fel
    szolg = source_chunk.get("szolgaltato") or ""
    doc_hint = ref.get("doc_hint")
    if doc_hint:
        target_doc = None
        for key in _doc_keys_from_hint(doc_hint):
            candidate = doc_name_index.get((szolg, key))
            if candidate:
                target_doc = candidate
                break
        if not target_doc:
            return None
    else:
        target_doc = source_chunk.get("doc_id")

    exact = paragraph_index.get((target_doc, paragraph))
    if exact:
        return exact
    for (doc_id, para), chunk in paragraph_index.items():
        if doc_id == target_doc and para.startswith(paragraph + "."):
            return chunk
    return None
```

- [ ] **Step 4: Run, expect PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reference_resolution.py -v`
Expected: 6 zöld.

- [ ] **Step 5: Commit**

```
git add backend/reference_resolution.py tests/test_reference_resolution.py
git commit -m "feat: reference resolution (doc-name + paragraph index, provider-scoped)"
```

---

## Task 3: `reference_closure` (`backend/reference_resolution.py`)

**Files:**
- Modify: `backend/reference_resolution.py`
- Test: `tests/test_reference_resolution.py`

- [ ] **Step 1: Failing test** — append to `tests/test_reference_resolution.py`:

```python
from backend.reference_resolution import reference_closure


def _corpus():
    return [
        {"chunk_id": "a1", "doc_id": "d", "szolgaltato": "ONE", "paragrafus_szam": "5.1",
         "source_file": "x.pdf", "text": "A 5.2 pont szerint.",
         "cross_refs": [{"raw": "5.2 pont", "doc_hint": None, "paragraph": "5.2"}]},
        {"chunk_id": "a2", "doc_id": "d", "szolgaltato": "ONE", "paragrafus_szam": "5.2",
         "source_file": "x.pdf", "text": "A határidő 30 nap.", "cross_refs": []},
    ]


def test_closure_pulls_linked_chunk():
    corpus = _corpus()
    seed = [dict(corpus[0], score=0.8)]
    added, unresolved = reference_closure(seed, corpus)
    assert len(added) == 1
    chunk, score = added[0]
    assert chunk["chunk_id"] == "a2"
    assert round(score, 2) == 0.75
    assert unresolved == []


def test_closure_collects_unresolved():
    corpus = _corpus()
    corpus[0]["cross_refs"] = [{"raw": "9.9 pont", "doc_hint": None, "paragraph": "9.9"}]
    seed = [dict(corpus[0], score=0.8)]
    added, unresolved = reference_closure(seed, corpus)
    assert added == []
    assert unresolved and unresolved[0]["paragraph"] == "9.9"


def test_closure_respects_max_extra():
    corpus = _corpus()
    # 6 különböző hivatkozás, de csak 5 húzható be
    extra = [{"chunk_id": f"e{i}", "doc_id": "d", "szolgaltato": "ONE", "paragrafus_szam": f"7.{i}",
              "source_file": "x.pdf", "text": "t", "cross_refs": []} for i in range(6)]
    corpus[0]["cross_refs"] = [{"raw": f"7.{i} pont", "doc_hint": None, "paragraph": f"7.{i}"} for i in range(6)]
    seed = [dict(corpus[0], score=0.8)]
    added, _ = reference_closure(seed, corpus + extra, max_extra=5)
    assert len(added) == 5


def test_closure_skips_chunk_already_in_seed():
    corpus = _corpus()
    seed = [dict(corpus[0], score=0.8), dict(corpus[1], score=0.7)]  # a2 már a seedben
    added, _ = reference_closure(seed, corpus)
    assert added == []
```

- [ ] **Step 2: Run, expect FAIL**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reference_resolution.py -k closure -v`
Expected: ImportError (`reference_closure`).

- [ ] **Step 3: Implement** — `backend/reference_resolution.py` végére:

```python
def reference_closure(
    seed_chunks: list[dict[str, Any]],
    all_chunks: list[dict[str, Any]],
    max_hops: int = 1,
    max_extra: int = 5,
) -> tuple[list[tuple[dict[str, Any], float]], list[dict[str, Any]]]:
    """1-hop referencia-lezárás: a seed chunkok hivatkozásait feloldja és behúzza.

    Visszatérés: (added, unresolved), ahol added = [(chunk, score), ...] (max_extra-ig),
    unresolved = a fel nem oldott hivatkozás-dictek. A behúzott score a seed score-ja − 0.05.
    """
    doc_name_index = build_doc_name_index(all_chunks)
    paragraph_index = build_paragraph_index(all_chunks)
    by_id = {str(c.get("chunk_id")): c for c in all_chunks if c.get("chunk_id")}
    seen = {str(c.get("chunk_id")) for c in seed_chunks if c.get("chunk_id")}

    added: list[tuple[dict[str, Any], float]] = []
    unresolved: list[dict[str, Any]] = []

    for seed in seed_chunks:
        source_chunk = by_id.get(str(seed.get("chunk_id")), seed)
        base_score = max(float(seed.get("score", 0.0)) - 0.05, 0.01)
        for ref in (source_chunk.get("cross_refs") or []):
            if len(added) >= max_extra:
                return added, unresolved
            target = resolve_reference(ref, source_chunk, doc_name_index, paragraph_index)
            if target is None:
                unresolved.append(ref)
                continue
            tid = str(target.get("chunk_id"))
            if tid in seen:
                continue
            seen.add(tid)
            added.append((target, base_score))
    return added, unresolved
```

- [ ] **Step 4: Run, expect PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reference_resolution.py -v`
Expected: 10 zöld.

- [ ] **Step 5: Commit**

```
git add backend/reference_resolution.py tests/test_reference_resolution.py
git commit -m "feat: 1-hop reference closure with bounded expansion and unresolved signal"
```

---

## Task 4: Retrieval-integráció (`backend/retrieval.py`)

**Files:**
- Modify: `backend/retrieval.py` (import; a `resolve_cross_refs` hívás cseréje; `unresolved_refs` a válaszba)
- Test: `tests/test_retrieval.py` (a `resolve_cross_refs` teszt cseréje closure-re)

- [ ] **Step 1: Update the test** — `tests/test_retrieval.py`-ban:

1. A `from backend.retrieval import hybrid_score, resolve_cross_refs, retrieve` sort cseréld:
```python
from backend.retrieval import hybrid_score, retrieve
from backend.reference_resolution import reference_closure
```
2. Cseréld le a teljes `test_resolve_cross_refs_adds_linked_chunk` függvényt erre:
```python
def test_reference_closure_adds_linked_chunk() -> None:
    corpus = [
        {"chunk_id": "doc_a_p0001_s001", "doc_id": "doc_a", "paragrafus_szam": "5.1",
         "text": "A 5.2 pont szerint.", "szolgaltato": "ONE", "source_file": "a.pdf",
         "cross_refs": [{"raw": "5.2 pont", "doc_hint": None, "paragraph": "5.2"}]},
        {"chunk_id": "doc_a_p0002_s001", "doc_id": "doc_a", "paragrafus_szam": "5.2",
         "text": "Az eljárás határideje 30 nap.", "szolgaltato": "ONE", "source_file": "a.pdf",
         "cross_refs": []},
    ]
    seed = [dict(corpus[0], score=0.8)]
    added, unresolved = reference_closure(seed, corpus)
    assert len(added) == 1
    assert added[0][0]["chunk_id"] == "doc_a_p0002_s001"
    assert unresolved == []
```

- [ ] **Step 2: Run, expect FAIL** (a `retrieve` még nem ad `unresolved_refs`-et; az új teszt importja is bukhat ha még nincs használatban — futtasd):

Run: `.venv/Scripts/python.exe -m pytest tests/test_retrieval.py -v`
Expected: a régi importra/függvényre hivatkozó rész piros, amíg a retrieval nem frissül.

- [ ] **Step 3: Implement** — `backend/retrieval.py`:

1. Add az importot a fájl tetejéhez (a `from config.settings import settings` mellé):
```python
from backend.reference_resolution import reference_closure
```
2. A `retrieve()` végén cseréld le ezt:
```python
    expanded = resolve_cross_refs(primary, all_chunks)
    return {
        "chunks": expanded,
        "retrieval_mode": retrieval_mode,
        "result_count": len(expanded),
    }
```
erre:
```python
    added, unresolved = reference_closure(primary, all_chunks)
    expanded = list(primary)
    for chunk, score in added:
        expanded.append(chunk_to_result(score, chunk) | {"retrieval_source": "reference_closure"})
    return {
        "chunks": expanded,
        "retrieval_mode": retrieval_mode,
        "result_count": len(expanded),
        "unresolved_refs": unresolved,
    }
```
3. Töröld a `resolve_cross_refs` függvényt és a már nem használt segédeit (`_chunk_index`, `_chunks_by_doc`, `_normalize_ref`, `CROSS_REF_LIMIT`, `REF_NUMBER_PATTERN`) — **csak ha** a `grep -rn "resolve_cross_refs\|_normalize_ref\|_chunks_by_doc" --include=*.py` szerint máshol nincs hivatkozás. Ha van, hagyd meg azokat.

- [ ] **Step 4: Run, expect PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_retrieval.py -v`
Expected: minden zöld (a closure-teszt + a meglévő retrieve-tesztek; az üres `cross_refs`-es chunkok `unresolved_refs: []`-t adnak).

- [ ] **Step 5: Commit**

```
git add backend/retrieval.py tests/test_retrieval.py
git commit -m "feat: retrieve() uses reference closure and returns unresolved_refs"
```

---

## Task 5: Backfill CLI a meglévő `chunks.jsonl`-hez (`preprocessing/enrich_cross_refs.py`)

**Files:**
- Create: `preprocessing/enrich_cross_refs.py`
- Test: `tests/test_enrich_cross_refs.py` (új)

- [ ] **Step 1: Failing test** — `tests/test_enrich_cross_refs.py`:

```python
import json
from preprocessing.enrich_cross_refs import enrich_chunks_file


def test_enrich_rewrites_cross_refs_from_text(tmp_path):
    rows = [
        {"chunk_id": "c1", "text": "A 5.6 pont és a 2/B. számú melléklet 4.1.4 pont szerint.", "cross_refs": []},
        {"chunk_id": "c2", "text": "Sima mondat.", "cross_refs": ["régi string"]},
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    count = enrich_chunks_file(path)

    out = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert count == 2
    assert isinstance(out[0]["cross_refs"], list) and isinstance(out[0]["cross_refs"][0], dict)
    assert any(r["paragraph"] == "5.6" for r in out[0]["cross_refs"])
    assert out[1]["cross_refs"] == []  # a régi string lecserélve, üresre (nincs hivatkozás a szövegben)
```

- [ ] **Step 2: Run, expect FAIL**

Run: `.venv/Scripts/python.exe -m pytest tests/test_enrich_cross_refs.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement** — `preprocessing/enrich_cross_refs.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.parse import extract_references

DEFAULT_CHUNKS_PATH = Path("data/processed/chunks.jsonl")


def enrich_chunks_file(path: Path = DEFAULT_CHUNKS_PATH) -> int:
    """A chunks.jsonl minden sorának cross_refs-ét újraszámolja a text-ből (strukturált). Visszaadja a feldolgozott sorok számát."""
    if not path.exists():
        return 0
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    for row in rows:
        row["cross_refs"] = extract_references(row.get("text", ""))
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill structured cross_refs into chunks.jsonl from text.")
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS_PATH))
    args = parser.parse_args()
    count = enrich_chunks_file(Path(args.chunks))
    print(f"Enriched {count} chunk(s) with structured cross_refs.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, expect PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_enrich_cross_refs.py -v`
Expected: 1 zöld.

- [ ] **Step 5: Commit**

```
git add preprocessing/enrich_cross_refs.py tests/test_enrich_cross_refs.py
git commit -m "feat: enrich_cross_refs backfill CLI for existing chunks.jsonl"
```

---

## Task 6: Adat-regenerálás + teljes verifikáció (operatív)

**Files:** (nincs új kód)

- [ ] **Step 1: Backfill a valós chunks.jsonl-en**

Run: `.venv/Scripts/python.exe -m preprocessing.enrich_cross_refs`
Expected: `Enriched 51049 chunk(s) ...`. (Készíts előtte biztonsági másolatot: `copy data\processed\chunks.jsonl data\processed\chunks.jsonl.bak`.)

- [ ] **Step 2: Ellenőrzés — strukturált cross_refs + closure él**

Run:
```
.venv/Scripts/python.exe -c "from preprocessing.index import load_chunks; c=load_chunks(); n=sum(1 for x in c if x.get('cross_refs')); print('cross_refs-szel:', n); ex=[x for x in c if x.get('cross_refs')][:1]; print(ex[0]['cross_refs'][:3] if ex else 'nincs')"
```
Expected: lényegesen több mint 142, és strukturált dict-ek.

- [ ] **Step 3: Qdrant re-index (payload-konzisztencia; a szöveg változatlan → embedding-cache)**

Run: `.venv/Scripts/python.exe -m preprocessing.index`
Expected: `Indexed N chunk(s) ...` hiba nélkül. (Ha a környezet nem indexel — pl. nincs Qdrant-írásjog —, a closure a lokális chunks.jsonl-ből akkor is működik; jegyezd fel.)

- [ ] **Step 4: Teljes backend suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: minden zöld, kivéve az ismert, független `test_settings_have_local_qdrant_defaults` (OPENAI_EMBED_DIM env).

- [ ] **Step 5: Élő smoke (ha a backend fut a 8000-en)**

Egy számlázási/felmondási kérdésre a `/agent/run` válaszában legyen legalább egy `retrieval_source: "reference_closure"` forrás VAGY `unresolved_refs` bejegyzés. (Ez bizonyítja a feature élő működését.)

- [ ] **Step 6: Commit (ha maradt nyitott)**

```
git add -A
git commit -m "chore: backfill structured cross_refs + reindex (reference closure live)" --allow-empty
```

---

## Önellenőrzés (spec-lefedettség)
- Strukturált `cross_refs` (str→dict), parse-extrakció → Task 1 ✓
- Dok-név index (provider-scoped, kétértelmű eldobva) + paragrafus-index + resolve → Task 2 ✓
- 1-hop, max +5 closure + unresolved → Task 3 ✓
- Retrieval-integráció + `unresolved_refs` + `reference_closure` forrás → Task 4 ✓
- Ingest-idejű regenerálás (backfill) + re-index → Task 5, 6 ✓
- Konzervatív feloldás (paragrafus nélkül / kétértelmű → unresolved), szolgáltató-szűrés → Task 2 tesztek ✓
- Hermetikus tesztek, re-index nélkül → Task 1–5 ✓
