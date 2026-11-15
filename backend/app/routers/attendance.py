"""Bulk attendance for one batch on one date."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.domain.actor import Actor, BranchScope
from app.schemas.operations import SheetPublic, SheetSave
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/sheets", response_model=SheetPublic)
def roster(
    batch_id: int,
    db: DbSession,
    attended_on: date,
    actor: Actor = Depends(require_permission("attendance:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SheetPublic:
    """Return the active roster with any marks already saved for that date."""
    return AttendanceService(db).roster(actor, scope, batch_id, attended_on)


@router.put("/sheets", response_model=SheetPublic)
def save_sheet(
    payload: SheetSave,
    db: DbSession,
    actor: Actor = Depends(require_permission("attendance:mark")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SheetPublic:
    """Save the register. Students without an active seat are rejected."""
    return AttendanceService(db).save(actor, scope, payload)
