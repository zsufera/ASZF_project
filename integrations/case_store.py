from typing import Protocol


class CaseStore(Protocol):
    def create_case(self, payload: dict) -> str:
        ...

    def get_case(self, case_id: str) -> dict | None:
        ...
