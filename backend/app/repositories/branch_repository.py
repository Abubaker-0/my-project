"""Branch queries."""

from __future__ import annotations

from sqlalchemy import func, or_, select

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

    def get_by_code(self, code: str) -> Branch | None:
        stmt = select(Branch).where(
            func.upper(Branch.code) == code.upper(),
            Branch.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def student_count(self, branch_id: int) -> int:
        from app.models.people import Student

        stmt = (
            select(func.count())
            .select_from(Student)
            .where(
                Student.branch_id == branch_id,
                Student.deleted_at.is_(None),
            )
        )
        return int(self.session.scalar(stmt) or 0)
