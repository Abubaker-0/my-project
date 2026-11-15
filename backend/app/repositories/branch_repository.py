"""Branch queries. Writes arrive with the organization module."""

from __future__ import annotations

from sqlalchemy import or_, select

from app.domain.actor import BranchScope
from app.models.branch import Branch
from app.repositories.base import Repository, apply_branch_scope


class BranchRepository(Repository):
    """Read access to campuses, already filtered by branch scope."""

    def list_branches(self, scope: BranchScope, *, q: str | None, offset: int, limit: int, order):
        stmt = select(Branch).where(Branch.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Branch.id, scope)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Branch.name.ilike(like), Branch.code.ilike(like)))
        stmt = stmt.order_by(order)
        return self.paginate(stmt, offset=offset, limit=limit)

    def get_visible(self, branch_id: int, scope: BranchScope) -> Branch | None:
        stmt = select(Branch).where(Branch.id == branch_id, Branch.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Branch.id, scope)
        return self.session.scalar(stmt)
