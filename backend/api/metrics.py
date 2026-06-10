from __future__ import annotations

from fastapi import APIRouter

from backend.metadata import response_meta
from backend.services.metrics_service import get_operational_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/operational")
def operational_metrics() -> dict:
    return {**response_meta(), **get_operational_metrics()}
