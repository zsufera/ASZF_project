from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from backend.api.schemas import (
    AcceptanceRequest,
    AgentRunRequest,
    CaseCreateRequest,
    CaseProcessRequest,
    ClassifyRequest,
    DemoRunRequest,
    DraftApproveRequest,
    DraftRequest,
    DraftSaveRequest,
    EvalBaselineRequest,
    EvalHumanScoreRequest,
    EvalRequest,
    FeedbackRequest,
    LoginRequest,
    MaskRequest,
    PolicyMapRequest,
    PurgeRequest,
    ReindexRequest,
    RetrieveRequest,
    SeedRequest,
    StatusTransitionRequest,
    UnmaskRequest,
    VerifyRequest,
)
from backend.audit_service import (
    build_case_audit_record,
    check_audit_completeness,
    list_audit_events,
    record_pii_access,
)
from backend.auth import ensure_users_in_db, get_user_id, get_user_role, verify_login
from backend.case_service import (
    create_ad_hoc_case,
    get_case_detail,
    list_inbox,
    submit_feedback,
    transition_case_status,
)
from backend.services.case_processing import approve_draft, process_case, save_draft_version
from backend.services.inbox_service import (
    get_supervisor_queue,
    get_supervisor_stats,
    seed_inbox_from_samples,
)
from backend.retention_service import purge_expired_records
from backend.workflow import WorkflowError
from backend.classify import classify_message
from backend.db import init_db
from backend.draft import synthesize_answer
from backend.api.agent import router as agent_router
from backend.api.cases import router as cases_router
from backend.api.copilot import router as copilot_router
from backend.api.history import router as history_router
from backend.api.knowledge import router as knowledge_router
from backend.api.metrics import router as metrics_router
from agent.runner import run_agent
from backend.acceptance_service import run_acceptance
from backend.eval_service import export_run, run_eval, set_baseline_from_run
from backend.tracing_service import list_recent_traces
from demo.runner import run_all_scenarios
from eval.report import load_baseline, save_human_score
from backend.history import get_history
from backend.masking import mask_text, unmask_text
from backend.metadata import response_meta
from backend.ocr_service import run_ocr
from backend.policy_map import build_policy_map
from backend.reindex_service import run_reindex
from backend.retrieval import refresh_chunk_cache, retrieve
from backend.verify import verify_draft
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory
from security.prompt_guard import detect_prompt_injection
from security.rbac import RBACError, require_permission

app = FastAPI(title="ASZF QnA Agent API", version="0.4.0")
POSTAL_PDF_DIR = Path("data/postal_pdfs")
app.include_router(cases_router)
app.include_router(history_router)
app.include_router(agent_router)
app.include_router(copilot_router)
app.include_router(knowledge_router)
app.include_router(metrics_router)


def _resolve_actor(username: str | None) -> tuple[int | None, str | None]:
    if not username:
        return None, None
    return get_user_id(username), get_user_role(username)


def _guard_permission(role: str | None, action: str) -> None:
    try:
        require_permission(role, action)  # type: ignore[arg-type]
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    ensure_users_in_db()
    seed_inbox_from_samples()
    POSTAL_PDF_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **response_meta()}


@app.post("/classify")
def classify(payload: ClassifyRequest) -> dict:
    injection = detect_prompt_injection(payload.message_text_masked)
    result = classify_message(
        message_text_masked=payload.message_text_masked,
        history_summary_masked=payload.history_summary_masked,
    )
    if injection["detected"]:
        result["prompt_injection_detected"] = True
        result["subtype"] = "prompt_injection"
    if payload.history_summary_masked and "ismetlodo" in payload.history_summary_masked.lower():
        result["is_repeated"] = True
    return {**response_meta(), **result}


@app.post("/retrieve")
def retrieve_endpoint(payload: RetrieveRequest) -> dict:
    result = retrieve(
        query=payload.query_masked,
        service_provider=payload.service_provider,
        limit=payload.limit,
    )
    return {**response_meta(), **result}


@app.post("/policy-map")
def policy_map(payload: PolicyMapRequest) -> dict:
    result = build_policy_map(category=payload.category, chunks=payload.chunks)
    return {**response_meta(), **result}


@app.post("/draft")
def draft(payload: DraftRequest) -> dict:
    result = synthesize_answer(
        case_id=payload.case_id,
        category=payload.category,
        channel=payload.channel,
        output_mode=payload.output_mode,
        policy_map=payload.policy_map,
        actions=payload.actions,
        input_text_masked=payload.input_text_masked,
    )
    return {**response_meta(), **result}


@app.post("/verify")
def verify(payload: VerifyRequest) -> dict:
    result = verify_draft(
        draft_body_masked=payload.draft_body_masked,
        chunks=payload.chunks,
        mandatory_refs=payload.mandatory_refs,
    )
    return {**response_meta(), **result}


@app.post("/mask")
def mask(payload: MaskRequest) -> dict:
    result = mask_text(case_id=payload.case_id, text=payload.text)
    return {**response_meta(), "masked_text": result["masked_text"], "token_count": result["token_count"]}


@app.post("/unmask")
def unmask(payload: UnmaskRequest) -> dict:
    role = payload.role or (get_user_role(payload.username) if payload.username else None)
    _guard_permission(role, "unmask")
    actor_id, _ = _resolve_actor(payload.username)
    record_pii_access(
        payload.case_id,
        action="unmask_endpoint",
        actor_user_id=actor_id,
        role=role,
        details={"draft_version_id": payload.draft_version_id},
    )
    subject = payload.subject_masked or ""
    body = payload.body_masked or ""
    if payload.draft_version_id is not None:
        with sqlite3.connect(settings.sqlite_path) as conn:
            row = conn.execute(
                """
                SELECT subject, body_masked
                FROM draft_versions
                WHERE id = ?
                """,
                (payload.draft_version_id,),
            ).fetchone()
        if row:
            subject = row[0] or ""
            body = row[1] or ""
    return {
        **response_meta(),
        "subject_unmasked": unmask_text(payload.case_id, subject),
        "body_unmasked": unmask_text(payload.case_id, body),
    }


@app.get("/history")
def history(address: str, sender_email_key: str | None = None) -> dict:
    return {**response_meta(), **get_history(address, sender_email_key=sender_email_key)}


@app.get("/customer-lookup")
def customer_lookup(address: str) -> dict:
    directory = MockCustomerDirectory()
    return {**response_meta(), "candidates": directory.lookup_by_email(address), "address": address}


@app.post("/ocr")
async def ocr(case_id: str = Form(...), pdf_file: UploadFile = File(...)) -> dict:
    target = POSTAL_PDF_DIR / f"{case_id}_{pdf_file.filename or 'upload.pdf'}"
    with target.open("wb") as handle:
        shutil.copyfileobj(pdf_file.file, handle)
    result = run_ocr(case_id=case_id, pdf_path=target)
    return {**response_meta(), **result}


@app.post("/reindex")
def reindex(payload: ReindexRequest) -> dict:
    result = run_reindex(force=payload.force)
    # Invalidate the in-memory chunk cache so the next retrieval picks up
    # the freshly indexed data without a backend restart.
    refresh_chunk_cache()
    return {**response_meta(), **result}


@app.post("/eval/run")
def eval_run(payload: EvalRequest) -> dict:
    result = run_eval(
        limit=payload.limit,
        category=payload.category,
        service_provider=payload.service_provider,
        include_edge=payload.include_edge,
        save_report=payload.save_report,
    )
    return {**response_meta(), **result}


@app.get("/eval/runs/{run_id}")
def eval_run_detail(run_id: str) -> dict:
    report = export_run(run_id)
    if not report:
        return {**response_meta(), "error": "Futás nem található", "run_id": run_id}
    return {**response_meta(), **report}


@app.get("/eval/baseline")
def eval_baseline() -> dict:
    baseline = load_baseline()
    if not baseline:
        return {**response_meta(), "has_baseline": False}
    return {**response_meta(), "has_baseline": True, **baseline}


@app.post("/eval/baseline")
def eval_baseline_save(payload: EvalBaselineRequest) -> dict:
    result = set_baseline_from_run(payload.run_id)
    if result.get("error"):
        return {**response_meta(), **result}
    return {**response_meta(), **result}


@app.post("/eval/human-score")
def eval_human_score(payload: EvalHumanScoreRequest) -> dict:
    return {**response_meta(), **save_human_score(payload.run_id, payload.email_id, payload.score)}


@app.post("/agent/run")
def agent_run(payload: AgentRunRequest) -> dict:
    if not payload.input_text and not payload.input_text_masked:
        return {**response_meta(), "error": "input_text vagy input_text_masked kötelező"}
    return run_agent(
        case_id=payload.case_id,
        channel=payload.channel,
        input_text=payload.input_text,
        input_text_masked=payload.input_text_masked,
        sender_email=payload.sender_email,
        service_provider=payload.service_provider,
        output_mode=payload.output_mode,
        selected_customer_id=payload.selected_customer_id,
        history_summary_masked=payload.history_summary_masked,
        sla_expired=payload.sla_expired,
    )


@app.post("/auth/login")
def auth_login(payload: LoginRequest) -> dict:
    user = verify_login(payload.username, payload.password)
    if not user:
        return {**response_meta(), "error": "Hibás felhasználónév vagy jelszó"}
    return {**response_meta(), **user, "user_id": get_user_id(user["username"])}


@app.post("/cases/seed")
def cases_seed(payload: SeedRequest) -> dict:
    return {**response_meta(), **seed_inbox_from_samples(force=payload.force)}


@app.get("/inbox")
def inbox(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    search: str | None = None,
    sort_by: str = "priority",
) -> dict:
    items = list_inbox(
        category=category,
        priority=priority,
        status=status,
        channel=channel,
        search=search,
        sort_by=sort_by,
    )
    return {**response_meta(), "items": items, "count": len(items)}


@app.get("/cases/{case_id}")
def case_detail(case_id: str) -> dict:
    detail = get_case_detail(case_id)
    if not detail:
        return {**response_meta(), "error": "Ügy nem található", "case_id": case_id}
    return {**response_meta(), **detail}


@app.post("/cases/create")
def case_create(payload: CaseCreateRequest) -> dict:
    case_id = create_ad_hoc_case(
        channel=payload.channel,
        input_text=payload.input_text,
        sender_email=payload.sender_email,
        service_provider=payload.service_provider,
    )
    return {**response_meta(), "case_id": case_id}


@app.post("/cases/process")
def case_process(payload: CaseProcessRequest) -> dict:
    actor_id, actor_role = _resolve_actor(payload.username)
    try:
        result = process_case(
            case_code=payload.case_id,
            output_mode=payload.output_mode,
            actor_user_id=actor_id,
            actor_role=actor_role,
            selected_customer_id=payload.selected_customer_id,
            service_provider=payload.service_provider,
            input_text_masked=payload.input_text_masked,
            sla_expired=payload.sla_expired,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {**response_meta(), **result}


@app.post("/cases/draft")
def case_draft_save(payload: DraftSaveRequest) -> dict:
    actor_id, actor_role = _resolve_actor(payload.username)
    try:
        result = save_draft_version(
            case_code=payload.case_id,
            subject=payload.subject,
            body_masked=payload.body_masked,
            output_mode=payload.output_mode,
            citations=payload.citations,
            actor_user_id=actor_id,
            actor_role=actor_role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {**response_meta(), **result}


@app.post("/cases/approve")
def case_approve(payload: DraftApproveRequest) -> dict:
    actor_id, actor_role = _resolve_actor(payload.username)
    try:
        result = approve_draft(
            case_code=payload.case_id,
            draft_version_id=payload.draft_version_id,
            subject_masked=payload.subject_masked,
            body_masked=payload.body_masked,
            actor_user_id=actor_id,
            actor_role=actor_role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {**response_meta(), **result}


@app.post("/cases/feedback")
def case_feedback(payload: FeedbackRequest) -> dict:
    actor_id = get_user_id(payload.username) if payload.username else None
    return {
        **response_meta(),
        **submit_feedback(
            case_code=payload.case_id,
            rating=payload.rating,
            wrong_source=payload.wrong_source,
            actor_user_id=actor_id,
        ),
    }


@app.get("/supervisor/queue")
def supervisor_queue() -> dict:
    items = get_supervisor_queue()
    return {**response_meta(), "items": items, "count": len(items)}


@app.get("/supervisor/stats")
def supervisor_stats() -> dict:
    return {**response_meta(), **get_supervisor_stats()}


@app.post("/cases/status")
def case_status_transition(payload: StatusTransitionRequest) -> dict:
    actor_id, actor_role = _resolve_actor(payload.username)
    _guard_permission(actor_role or payload.role, "change_status")
    try:
        result = transition_case_status(
            case_code=payload.case_id,
            target_status=payload.target_status,
            actor_user_id=actor_id,
            actor_role=actor_role or payload.role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return {**response_meta(), **result}


@app.get("/audit/cases/{case_id}")
def audit_case_record(case_id: str, role: str | None = None) -> dict:
    _guard_permission(role, "view_audit")
    record = build_case_audit_record(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Ügy nem található")
    return {**response_meta(), **record}


@app.get("/audit/events")
def audit_events(case_id: str | None = None, limit: int = 50, role: str | None = None) -> dict:
    _guard_permission(role, "view_audit")
    events = list_audit_events(case_code=case_id, limit=limit)
    return {**response_meta(), "events": events, "count": len(events)}


@app.get("/audit/completeness/{case_id}")
def audit_completeness(case_id: str, role: str | None = None) -> dict:
    _guard_permission(role, "view_audit")
    return {**response_meta(), **check_audit_completeness(case_id)}


@app.post("/governance/purge")
def governance_purge(payload: PurgeRequest) -> dict:
    role = payload.role or (get_user_role(payload.username) if payload.username else None)
    _guard_permission(role, "purge_retention")
    return {**response_meta(), **purge_expired_records(dry_run=payload.dry_run)}


@app.post("/acceptance/run")
def acceptance_run(payload: AcceptanceRequest) -> dict:
    return {
        **response_meta(),
        **run_acceptance(
            eval_limit=payload.eval_limit,
            include_edge=payload.include_edge,
            run_demo=payload.run_demo,
        ),
    }


@app.post("/demo/run")
def demo_run(payload: DemoRunRequest) -> dict:
    return {**response_meta(), **run_all_scenarios(save_report=payload.save_report)}


@app.get("/observability/traces")
def observability_traces(limit: int = 50) -> dict:
    traces = list_recent_traces(limit=limit)
    return {**response_meta(), "traces": traces, "count": len(traces)}
