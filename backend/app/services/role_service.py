"""Role administration and permission assignment."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.time import utcnow
from app.domain.actor import Actor
from app.models.rbac import Permission, Role
from app.repositories.rbac_repository import RbacRepository
from app.schemas.common import Page
from app.schemas.role import PermissionPublic, RoleCreate, RolePublic
from app.services.audit_service import AuditService
from app.services.presenters import to_role
from app.services.transactions import commit_or_conflict


class RoleService:
    """Creates roles and replaces their permission sets. Changes are audited."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.roles = RbacRepository(session)
        self.audit = AuditService(session)

    def list_roles(self, *, q: str | None, page: int, page_size: int, order) -> Page[RolePublic]:
        """Return one page of roles."""
        rows, total = self.roles.list_roles(
            q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[to_role(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_permissions(self) -> list[PermissionPublic]:
        """Return the full permission catalog. It is small enough for one page."""
        return [PermissionPublic.model_validate(item) for item in self.roles.list_permissions()]

    def create_role(self, actor: Actor, payload: RoleCreate) -> RolePublic:
        """Create a custom role. System role names are reserved by the seed."""
        if self.roles.get_role_by_name(payload.name) is not None:
            raise AppException(409, "CONFLICT", "A role with this name already exists")
        permissions = self._permissions(payload.permission_ids)
        role = Role(
            name=payload.name,
            label=payload.label.strip(),
            description=payload.description.strip(),
            is_system=False,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.session.add(role)
        self.session.flush()
        role.permissions = permissions
        self.audit.record(
            action="create",
            entity="role",
            entity_id=role.id,
            actor_id=actor.id,
            new_values={"name": role.name, "permissions": _codes(permissions)},
        )
        commit_or_conflict(self.session)
        created = self.roles.get_role(role.id)
        assert created is not None
        return to_role(created)

    def set_permissions(self, actor: Actor, role_id: int, permission_ids: list[int]) -> RolePublic:
        """Replace a role's permissions. Super Admin cannot be reduced."""
        role = self._get(role_id)
        if role.name == "super_admin":
            raise AppException(409, "CONFLICT", "Super Admin permissions cannot be changed")
        permissions = self._permissions(permission_ids)
        old_codes = _codes(role.permissions)
        new_codes = _codes(permissions)
        role.permissions = permissions
        role.updated_by = actor.id
        self.audit.record(
            action="permission_change",
            entity="role",
            entity_id=role.id,
            actor_id=actor.id,
            old_values={"permissions": old_codes},
            new_values={"permissions": new_codes},
        )
        commit_or_conflict(self.session)
        updated = self.roles.get_role(role.id)
        assert updated is not None
        return to_role(updated)

    def delete_role(self, actor: Actor, role_id: int) -> None:
        """Soft-delete a custom role that is not assigned."""
        role = self._get(role_id)
        if role.is_system:
            raise AppException(409, "CONFLICT", "System roles cannot be deleted")
        if self.roles.assignment_count(role.id) > 0:
            raise AppException(409, "CONFLICT", "Remove this role from users before deleting it")
        role.deleted_at = utcnow()
        role.updated_by = actor.id
        self.audit.record(
            action="delete",
            entity="role",
            entity_id=role.id,
            actor_id=actor.id,
            old_values={"name": role.name},
            new_values={"deleted": True},
        )
        commit_or_conflict(self.session)

    def _get(self, role_id: int) -> Role:
        role = self.roles.get_role(role_id)
        if role is None:
            raise AppException(404, "NOT_FOUND", "Role not found")
        return role

    def _permissions(self, permission_ids: list[int]) -> list[Permission]:
        found = self.roles.get_permissions_by_ids(permission_ids)
        if len(found) != len(set(permission_ids)):
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Unknown permission",
                details=[
                    {"field": "permission_ids", "message": "One or more permissions do not exist"}
                ],
            )
        return found


def _codes(permissions: list[Permission]) -> list[str]:
    return sorted(item.code for item in permissions)
