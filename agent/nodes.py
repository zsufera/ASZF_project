from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from agent.state import AgentState
from backend.classify import classify_message
from backend.draft import build_draft
from backend.escalation import decide_escalation
from backend.history import get_history
from backend.masking import mask_text, unmask_text
from backend.metadata import PROMPT_VERSION, load_manifest_summary
from backend.policy_map import build_policy_map, load_mandatory_refs
from backend.retrieval import retrieve
from backend.router import get_model_profile
from backend.verify import verify_draft
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory


DEFAULT_POLICIES_PATH = Path("config/policies.yaml")

ENGLISH_HINTS = ("dear", "hello", "please", "invoice", "billing", "thank you", "regards")
NEM_PANASZ_HINTS = ("köszön", "koszon", "köszönet", "kosznet", "megoldotta", "rendben volt")
HATOKORON_KIVULI_HINTS = ("munkahely", "hr ", "human resources", "fizetés nélküli", "fizetes nelkuli")
TRIGGER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "egyedi_szerzodes_gyanu": (
        "egyedi szerződés",
        "egyedi szerzodes",
        "egyedi kedvezmény",
        "aláírt szerződés",
        "egyedi, aláírt",
        "egyedi, alairt",
        "kedvezményes szerződést",
        "kedvezmenyes szerzodest",
        "egyedi előfizetői",
        "egyedi elofizetoi",
    ),
    "vitatott_osszeg": ("vitatott összeg", "vitatott osszeg", "jogvit", "visszatérítés", "visszaterites"),
    "jogi_hatosagi_media": ("bíróság", "birosag", "hatóság", "hatosag", "nmhh", "fogyasztóvédelem", "fogyvedelem"),
    "sla_kozel_lejarat": ("azonnal", "sürgős", "surgos", "határidő lejárt", "hatarido lejart"),
}
URGENT_HINTS = ("azonnal", "sürgős", "surgos", "hatóság", "hatosag", "bíróság", "birosag", "harmadszor", "ismét")


def _timeline_entry(step: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"step": step, "output": payload}


def _append_timeline(state: AgentState, step: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = list(state.get("timeline", []))
    timeline.append(_timeline_entry(step, payload))
    return timeline


def _active_text(state: AgentState) -> str:
    return state.get("input_text_masked") or state.get("input_text") or ""


def load_policies(path: Path = DEFAULT_POLICIES_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_mandatory_chunk_ids(category: str) -> list[str]:
    path = Path("config/mandatory_refs.yaml")
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = payload.get("mandatory_by_category", {}).get(category, []) or []
    chunk_ids: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("chunk_id"):
            chunk_ids.append(str(entry["chunk_id"]))
    return chunk_ids


def detect_trigger_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [name for name, keywords in TRIGGER_KEYWORDS.items() if any(keyword in lowered for keyword in keywords)]


def detect_lang_type(state: AgentState) -> AgentState:
    text = _active_text(state).lower()
    nyelv = "en" if any(hint in text for hint in ENGLISH_HINTS) else "hu"
    if any(hint in text for hint in NEM_PANASZ_HINTS):
        tipus = "nem_panasz"
    elif any(hint in text for hint in HATOKORON_KIVULI_HINTS):
        tipus = "hatokoron_kivuli"
    else:
        tipus = "panasz"
    payload = {"nyelv": nyelv, "tipus": tipus, "valasz_nyelv": "hu"}
    return {
        "lang_type": payload,
        "timeline": _append_timeline(state, "detect_lang_type", payload),
    }


def mask_input(state: AgentState) -> AgentState:
    if state.get("input_text_masked"):
        payload = {"skipped": True, "token_count": 0}
        return {"timeline": _append_timeline(state, "mask_input", payload)}

    raw_text = state.get("input_text") or ""
    masked = mask_text(state["case_id"], raw_text)
    payload = {"token_count": masked["token_count"], "token_types": masked["token_types"]}
    return {
        "input_text_masked": masked["masked_text"],
        "timeline": _append_timeline(state, "mask_input", payload),
    }


def load_context(state: AgentState) -> AgentState:
    sender = state.get("sender_email")
    history_summary = state.get("history_summary_masked")
    customer_candidates = list(state.get("customer_candidates") or [])
    payload: dict[str, Any] = {"history_loaded": False, "customer_count": len(customer_candidates)}

    if sender and not history_summary:
        history = get_history(sender)
        history_summary = history.get("summary_masked")
        payload["history_loaded"] = True
        payload["is_repeated"] = history.get("is_repeated", False)

    if sender and not customer_candidates:
        customer_candidates = MockCustomerDirectory().lookup_by_email(sender)
        payload["customer_count"] = len(customer_candidates)

    return {
        "history_summary_masked": history_summary,
        "customer_candidates": customer_candidates,
        "timeline": _append_timeline(state, "load_context", payload),
    }


def classify_node(state: AgentState) -> AgentState:
    result = classify_message(
        message_text_masked=_active_text(state),
        history_summary_masked=state.get("history_summary_masked"),
    )
    if state.get("lang_type", {}).get("tipus") == "nem_panasz":
        result["category"] = "egyeb"
        result["subtype"] = "nem_panasz"
    if state.get("lang_type", {}).get("tipus") == "hatokoron_kivuli":
        result["category"] = "egyeb"
        result["subtype"] = "hatokoron_kivuli"
    return {
        "classification": result,
        "timeline": _append_timeline(state, "classify", result),
    }


def priority_triage(state: AgentState) -> AgentState:
    text = _active_text(state).lower()
    classification = state.get("classification", {})
    reasons: list[str] = []
    if any(hint in text for hint in URGENT_HINTS):
        reasons.append("surgos_kulcsszo")
    if classification.get("is_repeated"):
        reasons.append("ismetlod_panasz")
    if detect_trigger_hits(text):
        reasons.append("eszkalacios_trigger_gyanu")
    value = "surgos" if reasons else "normal"
    payload = {"value": value, "reason": "; ".join(reasons) if reasons else "nincs sürgős jel"}
    return {
        "priority": payload,
        "timeline": _append_timeline(state, "priority_triage", payload),
    }


def retrieve_node(state: AgentState) -> AgentState:
    classification = state.get("classification", {})
    category = classification.get("category", "egyeb")
    query = _active_text(state)
    if len(query) > 400:
        query = f"{category} {query[:400]}"
    result = retrieve(
        query=query,
        service_provider=state.get("service_provider"),
        limit=5,
        prefer_qdrant=False,
    )
    return {
        "retrieval": result,
        "timeline": _append_timeline(state, "retrieve", {"result_count": result.get("result_count", 0)}),
    }


def policy_map_node(state: AgentState) -> AgentState:
    classification = state.get("classification", {})
    chunks = state.get("retrieval", {}).get("chunks", [])
    category = classification.get("category", "egyeb")
    result = build_policy_map(category=category, chunks=chunks)
    return {
        "policy_map": result,
        "timeline": _append_timeline(state, "policy_map", {"item_count": len(result.get("policy_items", []))}),
    }


def escalation_node(state: AgentState) -> AgentState:
    policies = load_policies()
    classification = state.get("classification", {})
    policy_map = state.get("policy_map", {})
    text = _active_text(state)
    trigger_hits = detect_trigger_hits(text)
    if classification.get("is_repeated"):
        trigger_hits.append("ismetlodo_panasz")
    if state.get("lang_type", {}).get("tipus") == "hatokoron_kivuli":
        trigger_hits.append("hatokoron_kivuli")

    result = decide_escalation(
        confidence=float(classification.get("confidence", 0.0)),
        confidence_threshold=float(policies.get("confidence_threshold", settings.confidence_threshold)),
        is_repeated=bool(classification.get("is_repeated")),
        missing_mandatory=list(policy_map.get("missing_mandatory", [])),
        sla_expired=bool(state.get("sla_expired")),
        trigger_hits=sorted(set(trigger_hits)),
    )
    return {
        "escalation": result,
        "timeline": _append_timeline(state, "escalation", result),
    }


def suggest_actions(state: AgentState) -> AgentState:
    escalation = state.get("escalation", {})
    lang_type = state.get("lang_type", {})
    actions: list[dict[str, Any]] = []

    if lang_type.get("tipus") == "nem_panasz":
        actions.append({"tipus": "koszonet_valasz", "indok": "Nem panasz üzenet – rövid visszajelzés.", "kockazat": "alacsony"})
    elif lang_type.get("tipus") == "hatokoron_kivuli":
        actions.append({"tipus": "eszkalacio", "indok": "Hatókörön kívüli kérés – emberi átadás.", "kockazat": "magas"})
    elif escalation.get("required"):
        actions.append({"tipus": "eszkalacio", "indok": "Eszkalációs trigger vagy alacsony konfidencia.", "kockazat": "magas"})
    else:
        actions.append({"tipus": "tajekoztatas", "indok": "Forrásolt tájékoztatás az ÁSZF alapján.", "kockazat": "alacsony"})
        if state.get("classification", {}).get("category") == "hibabejelentes_szolgaltataskieses":
            actions.append({"tipus": "visszahivas_technikus", "indok": "Hibabejelentés – technikus/visszahívás javasolt.", "kockazat": "kozepes"})

    return {
        "actions": actions,
        "timeline": _append_timeline(state, "suggest_actions", {"action_count": len(actions)}),
    }


def draft_node(state: AgentState) -> AgentState:
    channel = state.get("channel", "email")
    classification = state.get("classification", {})
    category = classification.get("category", "egyeb")
    policy_map = state.get("policy_map", {})
    actions = state.get("actions", [])
    output_mode = state.get("output_mode", "hitl")

    if channel in {"chat", "phone"}:
        policy_items = policy_map.get("policy_items", [])
        talking_points = [
            f"• {item.get('idezet', '')[:180]} (forrás: {item.get('chunk_id')})"
            for item in policy_items[:3]
            if item.get("idezet")
        ] or ["• Nincs elegendő forrás – eszkaláció javasolt."]
        result = {
            "subject": f"Copilot jegyzet – {category}",
            "body_masked": "Beszédpontok:\n" + "\n".join(talking_points),
            "citations": [item.get("chunk_id") for item in policy_items if item.get("chunk_id")],
            "disclaimer_applied": False,
            "format": "copilot",
        }
    else:
        result = build_draft(
            case_id=state["case_id"],
            category=category,
            output_mode=output_mode,
            policy_map=policy_map,
            actions=actions,
        )
        result["format"] = "email"

    return {
        "draft": result,
        "timeline": _append_timeline(state, "draft", {"format": result.get("format"), "citation_count": len(result.get("citations", []))}),
    }


def verify_node(state: AgentState) -> AgentState:
    draft = state.get("draft", {})
    chunks = state.get("retrieval", {}).get("chunks", [])
    category = state.get("classification", {}).get("category", "egyeb")
    mandatory_refs = load_mandatory_chunk_ids(category)
    if not mandatory_refs:
        mandatory_refs = [str(chunk_id) for chunk_id in draft.get("citations", []) if chunk_id]

    result = verify_draft(
        draft_body_masked=draft.get("body_masked", ""),
        chunks=chunks,
        mandatory_refs=mandatory_refs,
    )
    return {
        "verify": result,
        "timeline": _append_timeline(state, "verify", {"ungrounded_count": result.get("ungrounded_count", 0)}),
    }


def prepare_unmask(state: AgentState) -> AgentState:
    draft = state.get("draft", {})
    case_id = state["case_id"]
    preview = {
        "subject_unmasked": unmask_text(case_id, draft.get("subject", "")),
        "body_unmasked": unmask_text(case_id, draft.get("body_masked", "")),
        "ready_for_approval": True,
    }
    manifest = load_manifest_summary()
    audit_refs = {
        "prompt_version": PROMPT_VERSION,
        "model_profile": get_model_profile(),
        "aszf_version": manifest.get("aszf_version"),
    }
    return {
        "draft_preview_unmasked": preview,
        "audit_refs": audit_refs,
        "timeline": _append_timeline(state, "prepare_unmask", {"ready_for_approval": True}),
    }
