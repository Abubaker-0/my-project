"""FastAPI dependencies: database, current user, permission checks, branch scope."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.domain.actor import Actor, BranchScope
from app.domain.scope import scope_for
from app.repositories.user_repository import UserRepository
from app.services.presenters import actor_from_user

http_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: DbSession,
) -> Actor:
    """Load the caller from a bearer token. Permissions come from the database."""
    cached = getattr(request.state, "actor", None)
    if cached is not None:
        return cached
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException(401, "UNAUTHORIZED", "Authentication required")
    user_id = decode_access_token(credentials.credentials)
    user = UserRepository(db).get(user_id)
    if user is None or user.status != "active":
        raise AppException(401, "UNAUTHORIZED", "Authentication required")
    actor = actor_from_user(user)
    request.state.actor = actor
    return actor


CurrentActor = Annotated[Actor, Depends(get_current_actor)]


def require_permission(code: str):
    """Build a dependency that rejects callers missing `module:action`.

    Super Admin passes every check. Everyone else must hold the code through
    a role grant. The route still relies on repository scoping for row access.
    """

    def _checker(actor: CurrentActor) -> Actor:
        if not actor.has_permission(code):
            raise AppException(
                403,
                "FORBIDDEN",
                "You do not have permission to do that",
                details=[{"field": "permission", "message": code}],
            )
        return actor

    return _checker


def get_branch_scope(
    actor: CurrentActor,
    x_branch_id: Annotated[int | None, Header(alias="X-Branch-Id")] = None,
) -> BranchScope:
    """Apply the optional branch switcher without widening access."""
    return scope_for(actor, x_branch_id)


BranchFilter = Annotated[BranchScope, Depends(get_branch_scope)]
