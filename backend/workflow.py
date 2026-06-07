from __future__ import annotations

from typing import Literal

Status = Literal["uj", "folyamatban", "eszkalalva", "jovahagyasra_var", "lezarva"]

VALID_TRANSITIONS: dict[str, set[str]] = {
    "uj": {"folyamatban", "eszkalalva"},
    "folyamatban": {"eszkalalva", "jovahagyasra_var"},
    "eszkalalva": {"folyamatban", "jovahagyasra_var"},
    "jovahagyasra_var": {"lezarva", "folyamatban"},
    "lezarva": set(),
}


class WorkflowError(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def validate_transition(current: str, target: str) -> None:
    if current == target:
        return
    if not can_transition(current, target):
        raise WorkflowError(f"Érvénytelen státusz-átmenet: {current} → {target}")
