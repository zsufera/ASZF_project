from __future__ import annotations

TOOLS = [
    {"name": "classify", "description": "Determine complaint category and confidence.", "args": {}},
    {
        "name": "knowledge_search",
        "description": "Search ASZF sources for the question.",
        "args": {"category": "optional category"},
    },
    {
        "name": "customer_context",
        "description": "Load sender history and customer matches.",
        "args": {"sender_email": "sender email when available"},
    },
    {"name": "escalation_advice", "description": "Decide whether supervisor escalation is needed.", "args": {}},
    {
        "name": "draft_reply",
        "description": "Draft a sourced reply from the retrieved policy map.",
        "args": {"category": "optional category"},
    },
    {"name": "verify_grounding", "description": "Verify that the draft is grounded in sources.", "args": {}},
]


def tools_prompt() -> str:
    lines = ["Available tools:"]
    for tool in TOOLS:
        args = ", ".join(tool["args"]) if tool["args"] else "(no args)"
        lines.append(f'- {tool["name"]}: {tool["description"]} Args: {args}')
    return "\n".join(lines)
