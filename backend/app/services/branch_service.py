"""Read-only branch access for the shell. Writes arrive in the next phase."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor
from app.domain.scope import scope_for
from app.repositories.branch_repository import BranchRepository
from app.schemas.branch import BranchPublic
from app.schemas.common import Page
from app.services.presenters import to_branch


class BranchService:
    """Lists campuses the caller is allowed to see."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.branches = BranchRepository(session)

    def list_branches(
        self,
        actor: Actor,
        *,
        branch_id: int | None,
        q: str | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[BranchPublic]:
        """Return one page of branches inside the caller's scope."""
        scope = scope_for(actor, branch_id)
        rows, total = self.branches.list_branches(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[to_branch(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_branch(
        self, actor: Actor, branch_id: int, *, selected_branch_id: int | None
    ) -> BranchPublic:
        """Return one branch, or 404 when it is outside the caller's scope."""
        scope = scope_for(actor, selected_branch_id)
        branch = self.branches.get_visible(branch_id, scope)
        if branch is None:
            raise AppException(404, "NOT_FOUND", "Branch not found")
        return to_branch(branch)
