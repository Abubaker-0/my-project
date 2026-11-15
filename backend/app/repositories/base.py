"""Query helpers shared by repositories, including branch scoping."""

from __future__ import annotations

from sqlalchemy import Select, false, func, select
from sqlalchemy.orm import Session

from app.domain.actor import BranchScope


class Repository:
    """A session-bound data accessor. It does not commit."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, obj):
        self.session.add(obj)
        return obj

    def paginate(self, stmt: Select, *, offset: int, limit: int) -> tuple[list, int]:
        """Return the page of rows and the total count for an unordered statement."""
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int(self.session.scalar(count_stmt) or 0)
        rows = list(self.session.scalars(stmt.offset(offset).limit(limit)).unique().all())
        return rows, total


def apply_branch_scope(stmt: Select, column, scope: BranchScope) -> Select:
    """Limit a query to the caller's branches.

    Repositories call this for every business table that carries branch_id.
    An empty grant matches nothing, so a user with no branch cannot read rows
    by guessing ids.
    """
    if scope.unrestricted:
        return stmt
    if not scope.branch_ids:
        return stmt.where(false())
    return stmt.where(column.in_(scope.branch_ids))
