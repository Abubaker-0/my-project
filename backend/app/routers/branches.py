"""Branch routes used by the shell and campus setup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.branch import Branch
from app.schemas.branch import BranchPublic
from app.schemas.common import Page
from app.schemas.records import BranchCreate, BranchUpdate
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


@router.post("", response_model=BranchPublic, status_code=status.HTTP_201_CREATED)
def create_branch(
    payload: BranchCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("branches:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BranchPublic:
    """Create a campus. Super Admin is the role that holds this permission."""
    return BranchService(db).create_branch(actor, scope, payload)


@router.patch("/{branch_id}", response_model=BranchPublic)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("branches:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BranchPublic:
    """Update a campus the caller can access."""
    return BranchService(db).update_branch(actor, scope, branch_id, payload)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("branches:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a campus that has no students."""
    BranchService(db).delete_branch(actor, scope, branch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
