"""Audit log payloads."""

from __future__ import annotations

from typing import Any

from app.schemas.common import APIModel, UtcDateTime


class AuditLogPublic(APIModel):
    id: int
    user_id: int | None
    branch_id: int | None
    action: str
    entity: str
    entity_id: str | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip: str | None
    request_id: str | None
    created_at: UtcDateTime
