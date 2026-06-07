from __future__ import annotations

from typing import Any

from backend.case_service import create_ad_hoc_case, get_case_detail


class SQLiteCaseStore:
    def create_case(self, payload: dict[str, Any]) -> str:
        return create_ad_hoc_case(
            channel=payload.get("channel", "email"),
            input_text=payload.get("input_text", ""),
            sender_email=payload.get("sender_email"),
            service_provider=payload.get("service_provider"),
        )

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        return get_case_detail(case_id)
