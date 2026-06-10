from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.case_service import (
    assign_case,
    claim_case,
    create_ad_hoc_case,
    get_case_detail,
    list_inbox,
    release_case,
    submit_feedback,
    transition_case_status,
)
from backend.services.case_processing import approve_draft, process_case, save_draft_version
from backend.services.inbox_service import (
    get_supervisor_queue,
    get_supervisor_stats,
    seed_inbox_from_samples,
)
from backend.metadata import response_meta
from backend.workflow import WorkflowError
from security.rbac import RBACError

from .contracts import (
    CaseAssignRequest,
    CaseClaimRequest,
    CaseCreateRequest,
    CaseDetailResponse,
    CaseProcessRequest,
    CaseProcessResponse,
    CaseReleaseRequest,
    DraftApproveRequest,
    DraftApproveResponse,
    DraftSaveRequest,
    FeedbackRequest,
    InboxResponse,
    SeedRequest,
    StatusTransitionRequest,
)
from .deps import guard_permission, resolve_actor


router = APIRouter()


@router.post("/cases/seed")
def cases_seed(payload: SeedRequest) -> dict:
    return {**response_meta(), **seed_inbox_from_samples(force=payload.force)}


@router.get("/inbox", response_model=InboxResponse)
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


@router.post("/cases/claim")
def case_claim(payload: CaseClaimRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
    try:
        result = claim_case(
            case_code=payload.case_id,
            username=payload.username or "",
            actor_user_id=actor_id,
            actor_role=actor_role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return {**response_meta(), **result}


@router.post("/cases/assign")
def case_assign(payload: CaseAssignRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
    try:
        result = assign_case(
            case_code=payload.case_id,
            assignee_username=payload.assignee_username,
            actor_user_id=actor_id,
            actor_role=actor_role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return {**response_meta(), **result}


@router.post("/cases/release")
def case_release(payload: CaseReleaseRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
    try:
        result = release_case(
            case_code=payload.case_id,
            actor_user_id=actor_id,
            actor_role=actor_role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return {**response_meta(), **result}


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
def case_detail(case_id: str) -> dict:
    detail = get_case_detail(case_id)
    if not detail:
        return {**response_meta(), "error": "Ugy nem talalhato", "case_id": case_id}
    return {**response_meta(), **detail}


@router.post("/cases/create")
def case_create(payload: CaseCreateRequest) -> dict:
    case_id = create_ad_hoc_case(
        channel=payload.channel,
        input_text=payload.input_text,
        sender_email=payload.sender_email,
        service_provider=payload.service_provider,
    )
    return {**response_meta(), "case_id": case_id}


@router.post("/cases/process", response_model=CaseProcessResponse)
def case_process(payload: CaseProcessRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
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


@router.post("/cases/draft")
def case_draft_save(payload: DraftSaveRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
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


@router.post("/cases/approve", response_model=DraftApproveResponse)
def case_approve(payload: DraftApproveRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
    try:
        result = approve_draft(
            case_code=payload.case_id,
            draft_version_id=payload.draft_version_id,
            subject_masked=payload.subject_masked,
            body_masked=payload.body_masked,
            actor_user_id=actor_id,
            actor_role=actor_role or payload.role,
        )
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {**response_meta(), **result}


@router.post("/cases/feedback")
def case_feedback(payload: FeedbackRequest) -> dict:
    actor_id, _ = resolve_actor(payload.username)
    return {
        **response_meta(),
        **submit_feedback(
            case_code=payload.case_id,
            rating=payload.rating,
            wrong_source=payload.wrong_source,
            actor_user_id=actor_id,
        ),
    }


@router.get("/supervisor/queue")
def supervisor_queue() -> dict:
    items = get_supervisor_queue()
    return {**response_meta(), "items": items, "count": len(items)}


@router.get("/supervisor/stats")
def supervisor_stats() -> dict:
    return {**response_meta(), **get_supervisor_stats()}


@router.post("/cases/status")
def case_status_transition(payload: StatusTransitionRequest) -> dict:
    actor_id, actor_role = resolve_actor(payload.username)
    guard_permission(actor_role or payload.role, "change_status")
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

