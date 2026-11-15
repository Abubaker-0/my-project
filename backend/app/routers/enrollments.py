"""Enrollment, waitlist, withdrawal, and transfer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.enrollment import Enrollment
from app.schemas.common import Page
from app.schemas.records import (
    EnrollmentCreate,
    EnrollmentPublic,
    EnrollmentTransfer,
    EnrollmentWithdraw,
)
from app.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enrollments", tags=["enrollment"])

_SORT = {
    "enrolled_on": Enrollment.enrolled_on,
    "status": Enrollment.status,
    "created_at": Enrollment.created_at,
}


@router.get("", response_model=Page[EnrollmentPublic])
def list_enrollments(
    db: DbSession,
    actor: Actor = Depends(require_permission("enrollment:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
    batch_id: int | None = None,
    student_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> Page[EnrollmentPublic]:
    """List seats. Filter by batch, student, or status."""
    return EnrollmentService(db).list_enrollments(
        actor,
        scope,
        batch_id=batch_id,
        student_id=student_id,
        status=status_filter,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "-created_at"),
    )


@router.post("", response_model=EnrollmentPublic, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    payload: EnrollmentCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("enrollment:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> EnrollmentPublic:
    """Enroll a student. A full batch waitlists them."""
    return EnrollmentService(db).enroll(
        actor,
        scope,
        student_id=payload.student_id,
        batch_id=payload.batch_id,
        enrolled_on=payload.enrolled_on,
    )


@router.post("/{enrollment_id}/withdraw", response_model=EnrollmentPublic)
def withdraw_enrollment(
    enrollment_id: int,
    payload: EnrollmentWithdraw,
    db: DbSession,
    actor: Actor = Depends(require_permission("enrollment:withdraw")),
    scope: BranchScope = Depends(get_branch_scope),
) -> EnrollmentPublic:
    """Withdraw a seat and promote the next waiting student."""
    return EnrollmentService(db).withdraw(actor, scope, enrollment_id, payload.reason)


@router.post("/{enrollment_id}/transfer", response_model=EnrollmentPublic)
def transfer_enrollment(
    enrollment_id: int,
    payload: EnrollmentTransfer,
    db: DbSession,
    actor: Actor = Depends(require_permission("enrollment:transfer")),
    scope: BranchScope = Depends(get_branch_scope),
) -> EnrollmentPublic:
    """Move a seat to another batch at the same campus."""
    return EnrollmentService(db).transfer(actor, scope, enrollment_id, payload.batch_id)


@router.post("/{enrollment_id}/complete", response_model=EnrollmentPublic)
def complete_enrollment(
    enrollment_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("enrollment:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> EnrollmentPublic:
    """Mark a seat completed without offering it to the waitlist."""
    return EnrollmentService(db).complete(actor, scope, enrollment_id)
