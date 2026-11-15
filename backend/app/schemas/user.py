"""User account payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.common import APIModel, UtcDateTime


class RoleAssignmentIn(APIModel):
    role_id: int
    branch_id: int | None = None


class RoleAssignmentOut(APIModel):
    role_id: int
    role_name: str
    role_label: str
    branch_id: int | None
    branch_name: str | None


class UserCreate(APIModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    status: Literal["active", "inactive"] = "active"
    assignments: list[RoleAssignmentIn] = Field(min_length=1)


class UserUpdate(APIModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    status: Literal["active", "inactive"] | None = None
    assignments: list[RoleAssignmentIn] | None = None


class UserPublic(APIModel):
    id: int
    email: str
    full_name: str
    phone: str | None
    status: str
    last_login_at: UtcDateTime | None
    created_at: UtcDateTime
    roles: list[RoleAssignmentOut]


class UserSelf(UserPublic):
    """The signed-in account, including the permissions the interface may show."""

    permissions: list[str]
    all_branches: bool
    branch_ids: list[int]
