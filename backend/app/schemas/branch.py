"""Branch payloads. Creation belongs to the organization phase."""

from __future__ import annotations

from app.schemas.common import APIModel, UtcDateTime


class BranchPublic(APIModel):
    id: int
    code: str
    name: str
    address: str | None
    phone: str | None
    email: str | None
    status: str
    created_at: UtcDateTime
