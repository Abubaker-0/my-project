"""The authenticated caller, already resolved from the database."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleAssignment:
    """One role grant, global when branch_id is None."""

    role_id: int
    role_name: str
    role_label: str
    branch_id: int | None
    branch_name: str | None


@dataclass(frozen=True)
class Actor:
    """Identity and access used for permission and branch checks."""

    id: int
    email: str
    full_name: str
    status: str
    role_names: frozenset[str]
    permissions: frozenset[str]
    branch_ids: frozenset[int]
    all_branches: bool
    assignments: tuple[RoleAssignment, ...]

    @property
    def is_super_admin(self) -> bool:
        return "super_admin" in self.role_names

    def has_permission(self, code: str) -> bool:
        """Super Admin keeps every permission, including ones added after seeding."""
        return self.is_super_admin or code in self.permissions


@dataclass(frozen=True)
class BranchScope:
    """Row filter applied inside repositories.

    `unrestricted` is the Super Admin view across branches. Otherwise the query
    is limited to `branch_ids`. An empty list matches nothing.
    """

    unrestricted: bool
    branch_ids: tuple[int, ...]
