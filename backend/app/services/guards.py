"""Small checks shared by the academic services."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.core.exceptions import AppException
from app.core.time import utcnow
from app.domain.actor import BranchScope

_PHONE = re.compile(r"^[0-9+\-() ]{6,32}$")


def not_found(name: str) -> AppException:
    """Build the standard 404 for a missing or hidden row."""
    return AppException(404, "NOT_FOUND", f"{name} not found")


def clean_phone(value: str | None, field: str = "phone") -> str | None:
    """Normalize an optional phone number or reject it."""
    if value is None:
        return None
    phone = value.strip()
    if phone == "":
        return None
    if _PHONE.match(phone) is None:
        raise AppException(
            422,
            "VALIDATION_ERROR",
            "Enter a valid phone number",
            details=[{"field": field, "message": "Use digits and the characters + - ( )"}],
        )
    return phone


def ensure_branch(scope: BranchScope, branch_id: int) -> None:
    """Reject a branch id the caller did not grant themselves."""
    if scope.unrestricted or branch_id in scope.branch_ids:
        return
    raise AppException(403, "FORBIDDEN", "That branch is outside your access")


def stamp_new(row: Any, actor_id: int) -> None:
    """Set the audit users on a row that is about to be inserted."""
    row.created_by = actor_id
    row.updated_by = actor_id


def stamp_update(row: Any, actor_id: int) -> None:
    """Record who last changed a row."""
    row.updated_by = actor_id


def soft_delete(row: Any, actor_id: int) -> None:
    """Hide a row without removing it."""
    row.deleted_at = utcnow()
    row.updated_by = actor_id


def require_order(start: date, end: date, field: str) -> None:
    """Reject a range whose end is before its start."""
    if end < start:
        raise AppException(
            422,
            "VALIDATION_ERROR",
            "The end date must be on or after the start date",
            details=[{"field": field, "message": "End date is before the start date"}],
        )


def snapshot(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    """Copy the fields worth storing on an audit row."""
    values: dict[str, Any] = {}
    for name in fields:
        value = getattr(row, name)
        if isinstance(value, datetime | date):
            value = value.isoformat()
        values[name] = value
    return values
