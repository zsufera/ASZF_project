from __future__ import annotations

from typing import Literal

Role = Literal["ui", "supervisor"]
Action = Literal[
    "unmask",
    "approve_draft",
    "view_audit",
    "change_status",
    "purge_retention",
    "run_automata_mode",
]


class RBACError(PermissionError):
    pass


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ui": {
        "unmask",
        "approve_draft",
        "view_audit",
        "change_status",
        "run_automata_mode",
    },
    "supervisor": {
        "unmask",
        "approve_draft",
        "view_audit",
        "change_status",
        "purge_retention",
        "run_automata_mode",
    },
}


def has_permission(role: str | None, action: Action) -> bool:
    if not role:
        return False
    return action in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: str | None, action: Action) -> None:
    if not has_permission(role, action):
        raise RBACError(f"A(z) '{action}' művelet nem engedélyezett a(z) '{role}' szerepkörnek.")
