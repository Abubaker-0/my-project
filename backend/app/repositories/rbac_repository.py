"""Role and permission queries."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.rbac import Permission, Role, UserRole
from app.repositories.base import Repository


class RbacRepository(Repository):
    """All SQL for the permission catalog and roles."""

    def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.module, Permission.code)
        return list(self.session.scalars(stmt).all())

    def get_permissions_by_ids(self, ids: list[int]) -> list[Permission]:
        if not ids:
            return []
        stmt = select(Permission).where(Permission.id.in_(ids))
        return list(self.session.scalars(stmt).all())

    def get_role(self, role_id: int) -> Role | None:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id, Role.deleted_at.is_(None))
        )
        return self.session.scalar(stmt)

    def get_role_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name, Role.deleted_at.is_(None))
        )
        return self.session.scalar(stmt)

    def list_roles(self, *, q: str | None, offset: int, limit: int, order):
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.deleted_at.is_(None))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Role.name.ilike(like), Role.label.ilike(like)))
        stmt = stmt.order_by(order)
        return self.paginate(stmt, offset=offset, limit=limit)

    def assignment_count(self, role_id: int) -> int:
        stmt = select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
        return int(self.session.scalar(stmt) or 0)
