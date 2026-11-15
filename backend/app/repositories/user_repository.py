"""User and grant queries."""

from __future__ import annotations

from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import selectinload

from app.domain.actor import BranchScope
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.repositories.base import Repository

_USER_OPTIONS = (
    selectinload(User.role_links).selectinload(UserRole.role).selectinload(Role.permissions),
    selectinload(User.role_links).selectinload(UserRole.branch),
)


class UserRepository(Repository):
    """All SQL that reads or stages user rows."""

    def get(self, user_id: int, *, include_deleted: bool = False) -> User | None:
        stmt = select(User).options(*_USER_OPTIONS).where(User.id == user_id)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return self.session.scalar(stmt)

    def get_by_email(self, email: str, *, include_deleted: bool = False) -> User | None:
        stmt = select(User).options(*_USER_OPTIONS).where(User.email == email)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return self.session.scalar(stmt)

    def get_visible(self, user_id: int, scope: BranchScope) -> User | None:
        """Return a user only when the scope can see one of their branch grants."""
        stmt = (
            select(User)
            .options(*_USER_OPTIONS)
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        stmt = self._scope_users(stmt, scope)
        return self.session.scalar(stmt)

    def list_users(self, scope: BranchScope, *, q: str | None, offset: int, limit: int, order):
        stmt = select(User).options(*_USER_OPTIONS).where(User.deleted_at.is_(None))
        stmt = self._scope_users(stmt, scope)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(User.full_name.ilike(like), User.email.ilike(like), User.phone.ilike(like))
            )
        stmt = stmt.order_by(order)
        return self.paginate(stmt, offset=offset, limit=limit)

    def count_other_active_super_admins(self, excluding_user_id: int) -> int:
        stmt = (
            select(func.count(func.distinct(User.id)))
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.name == "super_admin",
                Role.deleted_at.is_(None),
                User.deleted_at.is_(None),
                User.status == "active",
                User.id != excluding_user_id,
            )
        )
        return int(self.session.scalar(stmt) or 0)

    def _scope_users(self, stmt, scope: BranchScope):
        if scope.unrestricted:
            return stmt
        if not scope.branch_ids:
            return stmt.where(false())
        visible_ids = select(UserRole.user_id).where(UserRole.branch_id.in_(scope.branch_ids))
        return stmt.where(User.id.in_(visible_ids))
