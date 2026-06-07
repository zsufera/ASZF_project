from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.nodes import (
    classify_node,
    detect_lang_type,
    draft_node,
    escalation_node,
    load_context,
    mask_input,
    policy_map_node,
    prepare_unmask,
    priority_triage,
    retrieve_node,
    suggest_actions,
    verify_node,
)
from agent.state import AgentState


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("detect_lang_type", detect_lang_type)
    graph.add_node("mask_input", mask_input)
    graph.add_node("load_context", load_context)
    graph.add_node("classify", classify_node)
    graph.add_node("priority_triage", priority_triage)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("policy_map", policy_map_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("suggest_actions", suggest_actions)
    graph.add_node("draft", draft_node)
    graph.add_node("verify", verify_node)
    graph.add_node("prepare_unmask", prepare_unmask)

    graph.set_entry_point("detect_lang_type")
    graph.add_edge("detect_lang_type", "mask_input")
    graph.add_edge("mask_input", "load_context")
    graph.add_edge("load_context", "classify")
    graph.add_edge("classify", "priority_triage")
    graph.add_edge("priority_triage", "retrieve")
    graph.add_edge("retrieve", "policy_map")
    graph.add_edge("policy_map", "escalation")
    graph.add_edge("escalation", "suggest_actions")
    graph.add_edge("suggest_actions", "draft")
    graph.add_edge("draft", "verify")
    graph.add_edge("verify", "prepare_unmask")
    graph.add_edge("prepare_unmask", END)

    return graph.compile()


compiled_agent_graph = build_agent_graph()
