"""Audit log queries. The table is append-only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, or_, select

from app.domain.actor import BranchScope
from app.models.audit import AuditLog
from app.repositories.base import Repository, apply_branch_scope


class AuditRepository(Repository):
    """Reads and stages audit rows. Updates are not offered."""

    def list_logs(
        self,
        scope: BranchScope,
        *,
        action: str | None,
        entity: str | None,
        q: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        offset: int,
        limit: int,
        order,
    ):
        stmt: Select = select(AuditLog)
        stmt = apply_branch_scope(stmt, AuditLog.branch_id, scope)
        if not scope.unrestricted:
            stmt = stmt.where(AuditLog.branch_id.is_not(None))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if entity:
            stmt = stmt.where(AuditLog.entity == entity)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(AuditLog.entity_id.ilike(like), AuditLog.action.ilike(like)))
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at <= date_to)
        stmt = stmt.order_by(order)
        return self.paginate(stmt, offset=offset, limit=limit)
