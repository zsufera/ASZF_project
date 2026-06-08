---
name: add-agent-node
description: Use when adding, removing, or reordering a node in the LangGraph agent pipeline (agent/graph.py + agent/nodes.py). Covers state I/O, the timeline entry, the frontend label mapping, and the structural test — so the new step shows up correctly in the UI and audit.
---

# Agent-node hozzáadása a LangGraph pipeline-hoz

A gráf **lineáris** (`agent/graph.py`, csak `add_edge`, nincs feltételes él). Egy node tiszta függvény: `AgentState → részleges AgentState` + **idővonal-bejegyzés**.

## Lépések

### 1. Írd meg a node-ot (`agent/nodes.py`)
```python
def my_node(state: AgentState) -> AgentState:
    text = _active_text(state)                 # maszkolt szöveg (input_text_masked || input_text)
    classification = state.get("classification", {})
    # ... tiszta logika; külső LLM esetén ld. az add-llm-call skillt ...
    payload = {"kulcs": ertek, ...}            # amit az idővonalon mutatunk
    return {
        "my_output": result,                   # új state-mező (vedd fel az AgentState-be is)
        "timeline": _append_timeline(state, "my_node", payload),
    }
```
- A node **ne** olvasson közvetlenül fájlt/DB-t inline — vékony adapteren át (guardrails §8).
- A maszkolás (`mask_input`) UTÁN minden LLM maszkolt szöveggel dolgozzon.

### 2. Kösd be a gráfba (`agent/graph.py`)
```python
graph.add_node("my_node", my_node)
# a megfelelő helyre fűzd a lineáris láncba:
graph.add_edge("előző", "my_node")
graph.add_edge("my_node", "következő")
```
A jelenlegi sorrend: `detect_lang_type → mask_input → load_context → classify → priority_triage → retrieve → policy_map → escalation → suggest_actions → draft → verify → prepare_unmask → END`.

### 3. Vedd fel a state-mezőt (`agent/state.py`) és — ha perzisztálni kell — a snapshotba (`agent/runner.py::persist_agent_run`).

### 4. Magyar címke a UI-hoz (`frontend/src/lib/agentSteps.ts`) — KÖTELEZŐ
Add hozzá a `STEP_META`-hoz (és a `PIPELINE_STEPS` sorrendhez), különben az idővonal a nyers `my_node` nevet mutatja:
```ts
my_node: {
  label: "Közérthető magyar cím",
  explain: "Egy mondat: mit csinál ez a lépés.",
  fields: ["kulcs"],   // mely payload-mezőket mutassuk lenyitáskor
},
```
Ha a payload új mezőt hoz, vedd fel a `FIELD_LABELS`-hez (és szükség esetén a `VALUE_MAPS`/`formatFieldValue`-hez) is.

### 5. Teszt (`tests/test_agent_graph.py` mintájára)
Strukturális assertek; a retrieve/LLM mockolva:
```python
def test_my_node(monkeypatch):
    state = {"case_id": "c", "input_text": "...", "classification": {"category": "szamlazas"}, "timeline": []}
    out = nodes.my_node(state)
    assert out["my_output"] == ...
    assert out["timeline"][-1]["step"] == "my_node"
```
Teljes-flow teszthez: `monkeypatch.setattr("agent.nodes.retrieve", _fake_retrieve)` (ld. a meglévő fixture-t), és asserts a `result["timeline"]` lépéssorrendjére.

## Ellenőrző lista
- [ ] node részleges state-et ad + `_append_timeline(...)`
- [ ] él bekötve a `graph.py`-ban; sorrend értelmes
- [ ] state-mező az `AgentState`-ben (+ snapshot, ha kell)
- [ ] `STEP_META` + `FIELD_LABELS` frissítve a frontenden
- [ ] strukturális teszt a node-ra és a lépéssorrendre
- [ ] auditálhatóság: az idővonal-payload tartalmazza a döntési okokat
