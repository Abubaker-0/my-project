"""User administration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserPublic, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

_SORT = {
    "full_name": User.full_name,
    "email": User.email,
    "status": User.status,
    "created_at": User.created_at,
    "last_login_at": User.last_login_at,
}


@router.get("", response_model=Page[UserPublic])
def list_users(
    db: DbSession,
    actor: Actor = Depends(require_permission("users:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[UserPublic]:
    """List accounts visible in the selected branch scope."""
    return UserService(db).list_users(
        actor,
        branch_id=None if scope.unrestricted else _selected(scope),
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "full_name"),
    )


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("users:create")),
) -> UserPublic:
    """Create an account and assign at least one role."""
    return UserService(db).create_user(actor, payload)


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("users:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> UserPublic:
    """Fetch one account inside the caller's branch scope."""
    return UserService(db).get_user(actor, user_id, branch_id=_selected(scope))


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("users:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> UserPublic:
    """Update profile fields or replace role grants."""
    return UserService(db).update_user(actor, user_id, payload, branch_id=_selected(scope))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("users:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Soft-delete an account. The row and its audit history stay in the database."""
    UserService(db).delete_user(actor, user_id, branch_id=_selected(scope))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/restore", response_model=UserPublic)
def restore_user(
    user_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("users:update")),
) -> UserPublic:
    """Restore a soft-deleted account. Restricted to Super Admin inside the service."""
    return UserService(db).restore_user(actor, user_id)


def _selected(scope: BranchScope) -> int | None:
    """Pass a single selected branch through. Unrestricted scope means no header."""
    if scope.unrestricted or len(scope.branch_ids) != 1:
        return None
    return scope.branch_ids[0]
