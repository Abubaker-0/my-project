"""Enrollment rules: capacity, waitlist, withdrawal, and transfer."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.time import utcnow
from app.domain.actor import Actor, BranchScope
from app.models.academics import Batch
from app.models.enrollment import Enrollment
from app.repositories.records import (
    BatchRepository,
    EnrollmentRepository,
    StudentRepository,
    lock_by_id,
)
from app.schemas.common import Page
from app.schemas.records import EnrollmentPublic
from app.services.audit_service import AuditService
from app.services.guards import not_found, snapshot, stamp_new, stamp_update
from app.services.transactions import commit_or_conflict

_OPEN_BATCH = {"planned", "active"}
_OPEN_SEAT = {"active", "waitlisted"}


class EnrollmentService:
    """Places students into batches without exceeding capacity.

    A seat is `active` while the batch has room. Further enrollments are
    `waitlisted` in arrival order. Withdrawing an active student promotes the
    earliest waiting student when the batch is still open. Closed seats are
    kept; they are never deleted.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.batches = BatchRepository(session)
        self.enrollments = EnrollmentRepository(session)
        self.students = StudentRepository(session)
        self.audit = AuditService(session)

    def list_enrollments(
        self,
        actor: Actor,
        scope: BranchScope,
        *,
        batch_id: int | None,
        student_id: int | None,
        status: str | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[EnrollmentPublic]:
        """Return one page of seats the caller is allowed to see."""
        rows, total = self.enrollments.list_enrollments(
            scope,
            actor,
            batch_id=batch_id,
            student_id=student_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            order=order,
        )
        return Page(
            items=[to_enrollment(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def enroll(
        self,
        actor: Actor,
        scope: BranchScope,
        *,
        student_id: int,
        batch_id: int,
        enrolled_on: date | None,
    ) -> EnrollmentPublic:
        """Give a student an active seat, or the next waitlist place."""
        row = self._seat(
            actor,
            scope,
            student_id=student_id,
            batch_id=batch_id,
            enrolled_on=enrolled_on or date.today(),
        )
        commit_or_conflict(self.session)
        loaded = self.enrollments.get_enrollment(row.id, scope, actor)
        assert loaded is not None
        return to_enrollment(loaded)

    def withdraw(
        self, actor: Actor, scope: BranchScope, enrollment_id: int, reason: str
    ) -> EnrollmentPublic:
        """Close a seat and promote the next waiting student when one is freed."""
        existing = self.enrollments.get_enrollment(enrollment_id, scope, actor)
        if existing is None:
            raise not_found("Enrollment")
        self._withdraw(actor, existing, reason.strip(), batch_locked=False)
        commit_or_conflict(self.session)
        self.session.refresh(existing)
        return to_enrollment(existing)

    def transfer(
        self, actor: Actor, scope: BranchScope, enrollment_id: int, target_batch_id: int
    ) -> EnrollmentPublic:
        """Move an open seat to another batch at the same campus.

        The student takes a seat in the destination first. The old seat is then
        withdrawn, which can promote someone who was waiting there. A full
        destination waitlists the student instead of keeping the old seat.
        """
        existing = self.enrollments.get_enrollment(enrollment_id, scope, actor)
        if existing is None:
            raise not_found("Enrollment")
        if existing.status not in _OPEN_SEAT:
            raise AppException(409, "CONFLICT", "Only an open seat can be transferred")
        if existing.batch_id == target_batch_id:
            raise AppException(409, "CONFLICT", "The student is already in that batch")
        self._lock_in_order(existing.batch_id, target_batch_id)
        target = self.session.get(Batch, target_batch_id)
        if target is None or target.deleted_at is not None:
            raise not_found("Batch")
        if target.branch_id != existing.branch_id:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Move the student to the other campus before enrolling them there",
                details=[{"field": "batch_id", "message": "Choose a batch at the same campus"}],
            )
        created = self._seat(
            actor,
            scope,
            student_id=existing.student_id,
            batch_id=target.id,
            enrolled_on=date.today(),
            locked=True,
        )
        self._withdraw(actor, existing, f"Transferred to {target.name}", batch_locked=True)
        self.audit.record(
            action="transfer",
            entity="enrollment",
            entity_id=created.id,
            actor_id=actor.id,
            branch_id=created.branch_id,
            old_values={"batch_id": existing.batch_id, "enrollment_id": existing.id},
            new_values={"batch_id": created.batch_id, "status": created.status},
        )
        commit_or_conflict(self.session)
        loaded = self.enrollments.get_enrollment(created.id, scope, actor)
        assert loaded is not None
        return to_enrollment(loaded)

    def complete(self, actor: Actor, scope: BranchScope, enrollment_id: int) -> EnrollmentPublic:
        """Mark a seat completed. The seat is not offered to the waitlist."""
        existing = self.enrollments.get_enrollment(enrollment_id, scope, actor)
        if existing is None:
            raise not_found("Enrollment")
        if existing.status != "active":
            raise AppException(409, "CONFLICT", "Only an active seat can be completed")
        locked = lock_by_id(self.session, Enrollment, existing.id)
        old = snapshot(locked, ("status",))
        locked.status = "completed"
        stamp_update(locked, actor.id)
        self.audit.record(
            action="update",
            entity="enrollment",
            entity_id=locked.id,
            actor_id=actor.id,
            branch_id=locked.branch_id,
            old_values=old,
            new_values={"status": "completed"},
        )
        commit_or_conflict(self.session)
        self.session.refresh(existing)
        return to_enrollment(existing)

    def fill_open_seats(self, actor: Actor, batch: Batch) -> None:
        """Promote waitlisted students until the batch is full or the list is empty."""
        while self._promote(actor, batch):
            pass

    def _seat(
        self,
        actor: Actor,
        scope: BranchScope,
        *,
        student_id: int,
        batch_id: int,
        enrolled_on: date,
        locked: bool = False,
    ) -> Enrollment:
        student = self.students.get_student(student_id, scope, actor)
        if student is None:
            raise not_found("Student")
        if student.status != "active":
            raise AppException(409, "CONFLICT", "Only an active student can be enrolled")
        batch = (
            self.session.get(Batch, batch_id)
            if locked
            else lock_by_id(self.session, Batch, batch_id)
        )
        if batch is None or batch.deleted_at is not None:
            raise not_found("Batch")
        if not scope.unrestricted and batch.branch_id not in scope.branch_ids:
            raise not_found("Batch")
        if batch.branch_id != student.branch_id:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "The student and the batch are in different branches",
                details=[
                    {"field": "batch_id", "message": "Choose a batch at the student's campus"}
                ],
            )
        if batch.status not in _OPEN_BATCH:
            raise AppException(409, "CONFLICT", "This batch is not open for enrollment")
        if self.batches.open_enrollment(student.id, batch.id) is not None:
            raise AppException(
                409,
                "CONFLICT",
                "This student already has a seat or a waitlist place in that batch",
            )
        status, position = self._placement(batch)
        row = Enrollment(
            branch_id=batch.branch_id,
            student_id=student.id,
            batch_id=batch.id,
            enrolled_on=enrolled_on,
            status=status,
            waitlist_position=position,
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self.audit.record(
            action="enroll" if status == "active" else "waitlist",
            entity="enrollment",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            new_values={
                "student_id": student.id,
                "batch_id": batch.id,
                "status": status,
                "waitlist_position": position,
            },
        )
        return row

    def _withdraw(
        self, actor: Actor, enrollment: Enrollment, reason: str, *, batch_locked: bool
    ) -> None:
        batch = (
            self.session.get(Batch, enrollment.batch_id)
            if batch_locked
            else lock_by_id(self.session, Batch, enrollment.batch_id)
        )
        current = lock_by_id(self.session, Enrollment, enrollment.id)
        if current is None or current.status not in _OPEN_SEAT:
            raise AppException(409, "CONFLICT", "That seat is already closed")
        was_active = current.status == "active"
        old = snapshot(current, ("status", "waitlist_position"))
        current.status = "withdrawn"
        current.withdrawal_reason = reason
        current.withdrawn_at = utcnow()
        current.waitlist_position = None
        stamp_update(current, actor.id)
        self.audit.record(
            action="withdraw",
            entity="enrollment",
            entity_id=current.id,
            actor_id=actor.id,
            branch_id=current.branch_id,
            old_values=old,
            new_values={"status": "withdrawn", "reason": reason},
        )
        self.session.flush()
        if was_active and batch is not None and batch.deleted_at is None:
            self._promote(actor, batch)

    def _placement(self, batch: Batch) -> tuple[str, int | None]:
        if self.batches.count_active(batch.id) < batch.capacity:
            return "active", None
        return "waitlisted", self.batches.next_waitlist_position(batch.id)

    def _promote(self, actor: Actor, batch: Batch) -> bool:
        if batch.status not in _OPEN_BATCH:
            return False
        if self.batches.count_active(batch.id) >= batch.capacity:
            return False
        waiting = self.batches.first_waitlisted(batch.id)
        if waiting is None:
            return False
        waiting.status = "active"
        waiting.waitlist_position = None
        stamp_update(waiting, actor.id)
        self.audit.record(
            action="promote",
            entity="enrollment",
            entity_id=waiting.id,
            actor_id=actor.id,
            branch_id=waiting.branch_id,
            new_values={"status": "active", "batch_id": batch.id, "student_id": waiting.student_id},
        )
        self.session.flush()
        return True

    def _lock_in_order(self, first_id: int, second_id: int) -> None:
        for batch_id in sorted({first_id, second_id}):
            lock_by_id(self.session, Batch, batch_id)


def to_enrollment(row: Enrollment) -> EnrollmentPublic:
    """Map a seat, including the student and course names the lists display."""
    return EnrollmentPublic(
        id=row.id,
        branch_id=row.branch_id,
        student_id=row.student_id,
        student_name=row.student.full_name,
        admission_no=row.student.admission_no,
        batch_id=row.batch_id,
        batch_name=row.batch.name,
        course_name=row.batch.course.name,
        status=row.status,
        waitlist_position=row.waitlist_position,
        enrolled_on=row.enrolled_on,
        withdrawal_reason=row.withdrawal_reason,
        created_at=row.created_at,
    )
