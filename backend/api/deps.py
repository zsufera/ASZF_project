from __future__ import annotations

from fastapi import HTTPException

from backend.auth import get_user_id, get_user_role
from security.rbac import RBACError, require_permission


def resolve_actor(username: str | None) -> tuple[int | None, str | None]:
    if not username:
        return None, None
    return get_user_id(username), get_user_role(username)


def guard_permission(role: str | None, action: str) -> None:
    try:
        require_permission(role, action)  # type: ignore[arg-type]
    except RBACError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
