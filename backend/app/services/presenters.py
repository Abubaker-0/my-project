"""Map ORM rows to response schemas."""

from __future__ import annotations

from app.db.catalog import all_permission_codes
from app.domain.actor import Actor, RoleAssignment
from app.models.audit import AuditLog
from app.models.branch import Branch
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.schemas.audit import AuditLogPublic
from app.schemas.branch import BranchPublic
from app.schemas.role import PermissionPublic, RolePublic
from app.schemas.user import RoleAssignmentOut, UserPublic, UserSelf


def actor_from_user(user: User) -> Actor:
    """Collect effective roles, permissions, and branch ids from eager-loaded grants."""
    assignments: list[RoleAssignment] = []
    permissions: set[str] = set()
    role_names: set[str] = set()
    branch_ids: set[int] = set()
    all_branches = False
    for link in user.role_links:
        role = link.role
        if role.deleted_at is not None:
            continue
        role_names.add(role.name)
        if link.branch_id is None:
            all_branches = True
        else:
            branch_ids.add(link.branch_id)
        permissions.update(permission.code for permission in role.permissions)
        assignments.append(
            RoleAssignment(
                role_id=role.id,
                role_name=role.name,
                role_label=role.label,
                branch_id=link.branch_id,
                branch_name=link.branch.name if link.branch is not None else None,
            )
        )
    if "super_admin" in role_names:
        all_branches = True
    return Actor(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        role_names=frozenset(role_names),
        permissions=frozenset(permissions),
        branch_ids=frozenset(branch_ids),
        all_branches=all_branches,
        assignments=tuple(assignments),
    )


def to_user_public(user: User) -> UserPublic:
    """Serialize a user without secrets."""
    roles = []
    for link in user.role_links:
        if link.role.deleted_at is not None:
            continue
        roles.append(_assignment(link))
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        status=user.status,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=roles,
    )


def to_user_self(user: User, actor: Actor) -> UserSelf:
    """Serialize the signed-in user, expanding Super Admin to the full catalog."""
    public = to_user_public(user)
    permissions = all_permission_codes() if actor.is_super_admin else sorted(actor.permissions)
    return UserSelf(
        **public.model_dump(),
        permissions=permissions,
        all_branches=actor.all_branches,
        branch_ids=sorted(actor.branch_ids),
    )


def to_role(role: Role) -> RolePublic:
    """Serialize a role and its permissions."""
    return RolePublic(
        id=role.id,
        name=role.name,
        label=role.label,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        permissions=[
            PermissionPublic(
                id=item.id, code=item.code, description=item.description, module=item.module
            )
            for item in sorted(role.permissions, key=lambda item: item.code)
        ],
    )


def to_branch(branch: Branch) -> BranchPublic:
    """Serialize a branch."""
    return BranchPublic.model_validate(branch)


def to_audit(row: AuditLog) -> AuditLogPublic:
    """Serialize an audit row."""
    return AuditLogPublic.model_validate(row)


def _assignment(link: UserRole) -> RoleAssignmentOut:
    return RoleAssignmentOut(
        role_id=link.role_id,
        role_name=link.role.name,
        role_label=link.role.label,
        branch_id=link.branch_id,
        branch_name=link.branch.name if link.branch is not None else None,
    )
