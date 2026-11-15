"""Branch read routes used by the shell."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.branch import Branch
from app.schemas.branch import BranchPublic
from app.schemas.common import Page
from app.services.branch_service import BranchService

router = APIRouter(prefix="/branches", tags=["branches"])

_SORT = {"name": Branch.name, "code": Branch.code, "created_at": Branch.created_at}


@router.get("", response_model=Page[BranchPublic])
def list_branches(
    db: DbSession,
    actor: Actor = Depends(require_permission("branches:read")),
    page=Depends(get_page_params),
) -> Page[BranchPublic]:
    """List every branch the caller can operate in.

    The branch switcher uses this list, so it ignores `X-Branch-Id`. Applying
    the header here would hide the other campuses after one is selected.
    """
    return BranchService(db).list_branches(
        actor,
        branch_id=None,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "name"),
    )


@router.get("/{branch_id}", response_model=BranchPublic)
def get_branch(
    branch_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("branches:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BranchPublic:
    """Fetch one branch inside the caller's scope."""
    selected = (
        scope.branch_ids[0] if not scope.unrestricted and len(scope.branch_ids) == 1 else None
    )
    return BranchService(db).get_branch(actor, branch_id, selected_branch_id=selected)
