from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.classify import classify_message
from backend.db import init_db
from backend.draft import build_draft
from backend.policy_map import build_policy_map
from backend.verify import verify_draft
from preprocessing.index import load_chunks, search_chunks


app = FastAPI(title="ASZF QnA Agent API", version="0.1.0")


class ClassifyRequest(BaseModel):
    case_id: str
    message_text_masked: str
    history_summary_masked: str | None = None


class RetrieveRequest(BaseModel):
    case_id: str
    query_masked: str
    service_provider: str | None = None
    customer_id: str | None = None


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


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/classify")
def classify(payload: ClassifyRequest) -> dict:
    result = classify_message(
        message_text_masked=payload.message_text_masked,
        history_summary_masked=payload.history_summary_masked,
    )
    return {
        "request_id": "stub",
        **result,
    }


@app.post("/retrieve")
def retrieve(payload: RetrieveRequest) -> dict:
    chunks = load_chunks()
    results = search_chunks(
        query=payload.query_masked,
        chunks=chunks,
        service_provider=payload.service_provider,
    )
    return {
        "request_id": "stub",
        "chunks": results,
    }


@app.post("/policy-map")
def policy_map(payload: PolicyMapRequest) -> dict:
    result = build_policy_map(category=payload.category, chunks=payload.chunks)
    return {"request_id": "stub", **result}


@app.post("/draft")
def draft(payload: DraftRequest) -> dict:
    result = build_draft(
        case_id=payload.case_id,
        category=payload.category,
        output_mode=payload.output_mode,
        policy_map=payload.policy_map,
        actions=payload.actions,
    )
    return {"request_id": "stub", **result}


@app.post("/verify")
def verify(payload: VerifyRequest) -> dict:
    result = verify_draft(
        draft_body_masked=payload.draft_body_masked,
        chunks=payload.chunks,
        mandatory_refs=payload.mandatory_refs,
    )
    return {"request_id": "stub", **result}


@app.get("/history")
def history(address: str) -> dict:
    return {"request_id": "stub", "items": [], "summary_masked": "", "is_repeated": False, "address": address}


@app.get("/customer-lookup")
def customer_lookup(address: str) -> dict:
    return {
        "request_id": "stub",
        "candidates": [
            {
                "customer_id": "CUST-DEMO-001",
                "customer_name": "Teszt Ugyfel",
                "link_url": "https://example.local/customer/CUST-DEMO-001",
                "source": "mock",
            }
        ],
        "address": address,
    }


@app.post("/ocr")
def ocr() -> dict:
    return {"request_id": "stub", "ocr_text_masked": "", "ocr_confidence": 0.0, "low_conf_spans": []}


@app.post("/unmask")
def unmask() -> dict:
    return {"request_id": "stub", "subject_unmasked": "", "body_unmasked": ""}


@app.post("/reindex")
def reindex() -> dict:
    return {"request_id": "stub", "aszf_version": None, "indexed_docs": 0, "indexed_chunks": 0}
