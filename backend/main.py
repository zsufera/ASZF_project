from fastapi import FastAPI
from pydantic import BaseModel

from backend.db import init_db
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


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/classify")
def classify(payload: ClassifyRequest) -> dict:
    return {
        "request_id": "stub",
        "category": "egyeb",
        "subtype": None,
        "confidence": 0.5,
        "candidates": [],
        "is_repeated": False,
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
def policy_map() -> dict:
    return {"request_id": "stub", "policy_items": [], "mandatory_refs": [], "missing_mandatory": []}


@app.post("/draft")
def draft() -> dict:
    return {"request_id": "stub", "subject": "", "body_masked": "", "citations": [], "disclaimer_applied": False}


@app.post("/verify")
def verify() -> dict:
    return {"request_id": "stub", "claims": [], "ungrounded_count": 0, "missing_mandatory": [], "warning": None}


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
