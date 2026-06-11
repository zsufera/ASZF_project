from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.nodes import HATOKORON_KIVULI_HINTS, detect_trigger_hits
from backend.classify import classify_message
from backend.draft import synthesize_answer
from backend.escalation import decide_escalation
from backend.metadata import PROMPT_VERSION, load_manifest_summary
from backend.policy_map import build_policy_map
from backend.retrieval import retrieve
from backend.verify import verify_draft
from config.settings import settings
from eval.judge import heuristic_judge_score
from eval.llm_judge import llm_judge_review
from eval.metrics import (
    compute_citation_support,
    compute_coverage,
    compute_faithfulness,
    compute_out_of_scope_violation,
    compute_retrieval_consistency,
    expected_escalation,
)
from eval.question_bank import load_question_bank
from eval.report import (
    aggregate_kpis,
    compare_with_baseline,
    load_baseline,
    load_run,
    load_targets,
    save_baseline,
    save_human_score,
    save_run,
)
from security.prompt_guard import detect_prompt_injection


DEFAULT_SAMPLE_DIR = Path("data/sample_emails")


def _detect_hatokoron(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in HATOKORON_KIVULI_HINTS)


def _mandatory_chunk_ids(category: str) -> list[str]:
    path = Path("config/mandatory_refs.yaml")
    if not path.exists():
        return []
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = payload.get("mandatory_by_category", {}).get(category, []) or []
    chunk_ids: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("chunk_id"):
            chunk_ids.append(str(entry["chunk_id"]))
    return chunk_ids


def evaluate_single(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    text = payload.get("torzs", "")
    edge_case = payload.get("edge_case")
    provider = payload.get("szolgaltato")

    injection = detect_prompt_injection(text)
    classification = classify_message(text)
    if injection["detected"]:
        classification["prompt_injection_detected"] = True
    if _detect_hatokoron(text):
        classification["category"] = "egyeb"
        classification["subtype"] = "hatokoron_kivuli"

    if edge_case == "ismetlodo_panasz":
        classification["is_repeated"] = True

    retrieval = retrieve(
        query=text,
        service_provider=provider,
        limit=5,
        prefer_qdrant=False,
    )
    chunks = retrieval.get("chunks", [])
    category = classification.get("category", "egyeb")
    policy_map = build_policy_map(category=category, chunks=chunks)

    trigger_hits = detect_trigger_hits(text)
    if edge_case == "ismetlodo_panasz":
        trigger_hits.append("ismetlodo_panasz")
    if classification.get("subtype") == "hatokoron_kivuli":
        trigger_hits.append("hatokoron_kivuli")

    escalation = decide_escalation(
        confidence=float(classification.get("confidence", 0.0)),
        confidence_threshold=settings.confidence_threshold,
        is_repeated=bool(classification.get("is_repeated")),
        missing_mandatory=list(policy_map.get("missing_mandatory", [])),
        sla_expired=False,
        trigger_hits=sorted(set(trigger_hits)),
    )

    actions = [{"tipus": "eszkalacio", "indok": "eval"}] if escalation.get("required") else [{"tipus": "tajekoztatas", "indok": "eval"}]
    draft = synthesize_answer(
        case_id=f"EVAL-{payload.get('email_id', 'unknown')}",
        category=category,
        channel="email",
        output_mode="hitl",
        policy_map=policy_map,
        actions=actions,
        input_text_masked=text,
    )
    mandatory_refs = _mandatory_chunk_ids(category) or [str(cid) for cid in draft.get("citations", []) if cid]
    verify = verify_draft(
        draft_body_masked=draft.get("body_masked", ""),
        chunks=chunks,
        mandatory_refs=mandatory_refs,
        citations=[str(cid) for cid in draft.get("citations", []) if cid],
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    expected_esc = expected_escalation(payload, classification)
    item = {
        "email_id": payload.get("email_id"),
        "edge_case": edge_case,
        "expected_category": payload.get("varht_kategoria"),
        "predicted_category": category,
        "category_match": category == payload.get("varht_kategoria"),
        "confidence": classification.get("confidence"),
        "retrieval_support": compute_retrieval_consistency(text, chunks),
        "retrieval_mode": retrieval.get("retrieval_mode"),
        "citation_support": compute_citation_support(draft, chunks),
        "faithfulness": compute_faithfulness(verify),
        "ungrounded_count": verify.get("ungrounded_count", 0),
        "escalation_required": escalation.get("required"),
        "escalation_expected": expected_esc,
        "escalation_appropriate": escalation.get("required") == expected_esc,
        "escalation_reasons": escalation.get("reasons", []),
        "coverage": compute_coverage(chunks, draft, escalation.get("required", False), edge_case),
        "out_of_scope_violation": compute_out_of_scope_violation(
            edge_case, escalation.get("required", False), draft
        ),
        "prompt_injection_detected": injection["detected"],
        "time_to_answer_ms": elapsed_ms,
        "service_provider": provider,
    }
    item["judge_score"] = heuristic_judge_score(item)
    judge_review = llm_judge_review(text, draft.get("body_masked", ""), chunks)
    item["llm_judge_score"] = judge_review["score"] if judge_review else None
    item["llm_judge_indoklas"] = judge_review["indoklas"] if judge_review else None
    item["judge_mode"] = "llm" if judge_review else "heuristic"
    return item


def run_eval(
    sample_dir: Path = DEFAULT_SAMPLE_DIR,
    limit: int = 10,
    category: str | None = None,
    service_provider: str | None = None,
    include_edge: bool = True,
    save_report: bool = True,
) -> dict[str, Any]:
    bank = load_question_bank(
        sample_dir=sample_dir,
        limit=limit,
        category=category,
        service_provider=service_provider,
        include_edge=include_edge,
    )
    results = [evaluate_single(payload) for payload in bank]
    targets = load_targets()
    kpis = aggregate_kpis(results, targets)
    manifest = load_manifest_summary()
    baseline = load_baseline()
    if baseline and baseline.get("aszf_version") != manifest.get("aszf_version"):
        kpis["values"]["version_mismatch"] = 1

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evaluated": len(results),
        "filters": {
            "limit": limit,
            "category": category,
            "service_provider": service_provider,
            "include_edge": include_edge,
        },
        "prompt_version": PROMPT_VERSION,
        "aszf_version": manifest.get("aszf_version"),
        "kpis": kpis,
        "baseline_diff": compare_with_baseline(kpis),
        "results": results,
        # Backward-compatible top-level fields
        "category_accuracy": kpis["values"]["category_accuracy"],
        "retrieval_support": kpis["values"]["retrieval_support"],
    }
    if save_report:
        save_run(report)
    return report


def export_run(run_id: str) -> dict[str, Any] | None:
    return load_run(run_id)


def set_baseline_from_run(run_id: str) -> dict[str, Any]:
    report = load_run(run_id)
    if not report:
        return {"error": "Futás nem található", "run_id": run_id}
    return save_baseline(report)
