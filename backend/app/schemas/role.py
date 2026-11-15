"""Role and permission payloads."""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel, UtcDateTime


class PermissionPublic(APIModel):
    id: int
    code: str
    description: str
    module: str


class RoleCreate(APIModel):
    name: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    permission_ids: list[int] = Field(default_factory=list)


class RolePermissionsUpdate(APIModel):
    permission_ids: list[int]


class RolePublic(APIModel):
    id: int
    name: str
    label: str
    description: str
    is_system: bool
    permissions: list[PermissionPublic]
    created_at: UtcDateTime
