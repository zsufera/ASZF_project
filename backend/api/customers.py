from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.metadata import response_meta
from integrations.customer_directory import MockCustomerDirectory


router = APIRouter()


@router.get("/customers/{customer_id}")
def customer_detail(customer_id: str) -> dict:
    customer = MockCustomerDirectory().get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Ugyfel nem talalhato")
    return {**response_meta(), **customer}
