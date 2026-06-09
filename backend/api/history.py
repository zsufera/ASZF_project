from __future__ import annotations

from fastapi import APIRouter

from backend.history import get_history
from backend.metadata import response_meta

from .contracts import HistoryResponse


router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
def history(address: str, sender_email_key: str | None = None) -> dict:
    return {**response_meta(), **get_history(address, sender_email_key=sender_email_key)}
