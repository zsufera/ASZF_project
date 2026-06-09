from __future__ import annotations

import json
import logging
from typing import Any

from agent.copilot import tools_spec
from agent.copilot.session import CopilotSession
from agent.copilot.subagents import SUBAGENTS
from backend.llm import chat_json, llm_available
from backend.modes import OrchestratorMode

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8

ORCHESTRATOR_SYSTEM = (
    "You are an internal customer-service Copilot orchestrator. Decide exactly one next step as JSON:\n"
    '{"action":"call_tool","tool":"<name>","args":{...}}\n'
    '{"action":"respond","reply":"<final internal answer>"}\n'
    '{"action":"ask_user","question":"<clarifying question>"}\n'
    "Only call listed tools. Do not invent facts. Preserve source markers like [S1]. "
    "Keep masked PII tokens unchanged.\n"
    + tools_spec.tools_prompt()
)


def _observation_block(observations: list[dict[str, Any]]) -> str:
    if not observations:
        return "(no tool results yet)"
    return "\n".join(
        f'- {obs["tool"]} -> {json.dumps(obs["result"], ensure_ascii=False)[:600]}'
        for obs in observations
    )


def _decide(session: CopilotSession, observations: list[dict[str, Any]]) -> dict[str, Any]:
    user = (
        f'Operator question (masked):\n"""\n{session.message_masked}\n"""\n'
        f"Conversation history:\n{json.dumps(session.history, ensure_ascii=False)[:1000]}\n"
        f"Tool observations:\n{_observation_block(observations)}\n"
        "What is your next decision?"
    )
    return chat_json(ORCHESTRATOR_SYSTEM, user)


def _fallback_reply(session: CopilotSession) -> str:
    if session.draft and session.draft.get("body_masked"):
        return session.draft["body_masked"]
    return (
        "Nincs elegendo ASZF-fedezet automatikus valaszhoz. "
        "Emberi ellenorzes / eszkalacio javasolt."
    )


def _source_refs(session: CopilotSession) -> list[dict[str, Any]]:
    if session.draft and session.draft.get("sources"):
        return list(session.draft.get("sources") or [])
    policy_items = (session.retrieval or {}).get("policy_map", {}).get("policy_items", [])
    sources: list[dict[str, Any]] = []
    for item in policy_items:
        if not item.get("chunk_id"):
            continue
        sources.append(
            {
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
            }
        )
    return sources


def _finalize(session: CopilotSession, reply_masked: str, mode: str) -> dict[str, Any]:
    return {
        "reply_masked": reply_masked,
        "sources": _source_refs(session),
        "draft": session.draft,
        "escalation": session.escalation,
        "timeline": session.timeline,
        "orchestrator_mode": mode,
    }


def _run_fallback(session: CopilotSession) -> dict[str, Any]:
    SUBAGENTS["classify"](session)
    SUBAGENTS["knowledge_search"](session)
    escalation = SUBAGENTS["escalation_advice"](session)
    if not escalation["required"]:
        SUBAGENTS["draft_reply"](session)
    return _finalize(session, _fallback_reply(session), OrchestratorMode.FALLBACK)


def run(session: CopilotSession) -> dict[str, Any]:
    if not llm_available():
        return _run_fallback(session)

    observations: list[dict[str, Any]] = []
    for _ in range(MAX_ITERATIONS):
        try:
            decision = _decide(session, observations)
        except Exception:
            logger.exception("orchestrator decision failed; switching to fallback")
            return _run_fallback(session)

        action = decision.get("action")
        if action == "respond":
            return _finalize(session, str(decision.get("reply", "")).strip(), OrchestratorMode.LLM)
        if action == "ask_user":
            return _finalize(session, str(decision.get("question", "")).strip(), OrchestratorMode.LLM)
        if action == "call_tool":
            tool = str(decision.get("tool") or "")
            subagent = SUBAGENTS.get(tool)
            if not subagent:
                observations.append({"tool": tool, "result": {"error": "unknown tool"}})
                continue
            args = decision.get("args") or {}
            try:
                result = subagent(session, **args)
            except Exception as exc:
                logger.exception("subagent %s failed", tool)
                result = {"error": str(exc)}
            observations.append({"tool": tool, "result": result})
            continue
        break

    session.record(
        step="iteration_cap",
        output={"iterations": MAX_ITERATIONS},
        status="warning",
        summary="iteration cap reached",
    )
    return _finalize(session, _fallback_reply(session), OrchestratorMode.LLM)
