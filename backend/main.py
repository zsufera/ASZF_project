from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel, Field

from backend.classify import classify_message
from backend.db import init_db
from backend.draft import build_draft
from backend.eval_service import run_eval
from backend.history import get_history
from backend.masking import mask_text, unmask_text
from backend.metadata import response_meta
from backend.ocr_service import run_ocr
from backend.policy_map import build_policy_map
from backend.reindex_service import run_reindex
from backend.retrieval import retrieve
from backend.verify import verify_draft
from config.settings import settings
from integrations.customer_directory import MockCustomerDirectory


app = FastAPI(title="ASZF QnA Agent API", version="0.2.0")
POSTAL_PDF_DIR = Path("data/postal_pdfs")


class ClassifyRequest(BaseModel):
    case_id: str
    message_text_masked: str
    history_summary_masked: str | None = None


class RetrieveRequest(BaseModel):
    case_id: str
    query_masked: str
    service_provider: str | None = None
    customer_id: str | None = None
    limit: int = 5


class PolicyMapRequest(BaseModel):
    case_id: str
    category: str
    chunks: list[dict]


class DraftRequest(BaseModel):
    case_id: str
    category: str
    output_mode: str
    policy_map: dict
    actions: list[dict] = Field(default_factory=list)


class VerifyRequest(BaseModel):
    case_id: str
    draft_body_masked: str
    chunks: list[dict]
    mandatory_refs: list[str]


class MaskRequest(BaseModel):
    case_id: str
    text: str


class UnmaskRequest(BaseModel):
    case_id: str
    draft_version_id: int | None = None
    subject_masked: str | None = None
    body_masked: str | None = None


class ReindexRequest(BaseModel):
    force: bool = False


class EvalRequest(BaseModel):
    limit: int = 10


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    POSTAL_PDF_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **response_meta()}


@app.post("/classify")
def classify(payload: ClassifyRequest) -> dict:
    result = classify_message(
        message_text_masked=payload.message_text_masked,
        history_summary_masked=payload.history_summary_masked,
    )
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
    result = build_draft(
        case_id=payload.case_id,
        category=payload.category,
        output_mode=payload.output_mode,
        policy_map=payload.policy_map,
        actions=payload.actions,
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
def history(address: str) -> dict:
    return {**response_meta(), **get_history(address)}


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
    return {**response_meta(), **result}


@app.post("/eval/run")
def eval_run(payload: EvalRequest) -> dict:
    result = run_eval(limit=payload.limit)
    return {**response_meta(), **result}
