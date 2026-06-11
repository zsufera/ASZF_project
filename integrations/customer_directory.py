from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol


class CustomerDirectory(Protocol):
    def lookup_by_email(self, address: str) -> list[dict]:
        ...

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        ...


MOCK_CUSTOMERS_PATH = Path("data/mock_customers.json")


@lru_cache(maxsize=1)
def _load_mock_customers() -> list[dict[str, Any]]:
    if not MOCK_CUSTOMERS_PATH.exists():
        return []
    payload = json.loads(MOCK_CUSTOMERS_PATH.read_text(encoding="utf-8"))
    return list(payload.get("customers") or [])


def _candidate_from_customer(customer: dict[str, Any]) -> dict[str, Any]:
    customer_id = str(customer["customer_id"])
    return {
        "customer_id": customer_id,
        "customer_name": customer["customer_name"],
        "link_url": f"/customer/{customer_id}",
        "source": "mock",
    }


class MockCustomerDirectory:
    def lookup_by_email(self, address: str) -> list[dict]:
        normalized = (address or "").strip().lower()
        return [
            _candidate_from_customer(customer)
            for customer in _load_mock_customers()
            if str(customer.get("primary_email") or "").lower() == normalized
        ]

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        for customer in _load_mock_customers():
            if customer.get("customer_id") == customer_id:
                return {**customer, "link_url": f"/customer/{customer_id}"}
        return None
