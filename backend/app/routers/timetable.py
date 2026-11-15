"""Weekly timetable."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.operations import ClassSession
from app.schemas.common import Page
from app.schemas.operations import SessionCreate, SessionPublic, SessionUpdate
from app.services.timetable_service import TimetableService

router = APIRouter(prefix="/timetable/sessions", tags=["timetable"])

_SORT = {
    "weekday": ClassSession.weekday,
    "start_time": ClassSession.start_time,
    "created_at": ClassSession.created_at,
}


@router.get("", response_model=Page[SessionPublic])
def list_sessions(
    db: DbSession,
    actor: Actor = Depends(require_permission("timetable:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
    batch_id: int | None = None,
) -> Page[SessionPublic]:
    """List weekly slots the caller is allowed to see."""
    return TimetableService(db).list_sessions(
        actor,
        scope,
        batch_id=batch_id,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "weekday"),
    )


@router.post("", response_model=SessionPublic, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("timetable:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SessionPublic:
    """Add a weekly slot. The room and the teacher must both be free."""
    return TimetableService(db).create_session(actor, scope, payload)


@router.patch("/{session_id}", response_model=SessionPublic)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("timetable:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SessionPublic:
    """Move a scheduled slot. The overlap rules apply to the new time."""
    return TimetableService(db).update_session(actor, scope, session_id, payload)


@router.post("/{session_id}/cancel", response_model=SessionPublic)
def cancel_session(
    session_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("timetable:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SessionPublic:
    """Cancel a slot. The row stays, and the room becomes free."""
    return TimetableService(db).cancel_session(actor, scope, session_id)
