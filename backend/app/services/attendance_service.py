"""Bulk attendance for the students who hold an active seat."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.access import limits_to_assigned_batches
from app.domain.actor import Actor, BranchScope
from app.models.operations import AttendanceMark, AttendanceSheet
from app.repositories.operations import AttendanceRepository
from app.repositories.records import BatchRepository, assigned_batch_ids
from app.schemas.operations import MarkPublic, SheetPublic, SheetSave
from app.services.audit_service import AuditService
from app.services.guards import not_found, stamp_new, stamp_update
from app.services.transactions import commit_or_conflict


class AttendanceService:
    """Saves a whole register in one transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AttendanceRepository(session)
        self.batches = BatchRepository(session)
        self.audit = AuditService(session)

    def roster(self, actor: Actor, scope: BranchScope, batch_id: int, attended_on) -> SheetPublic:
        batch = self._batch(actor, scope, batch_id)
        sheet = self.repo.get_sheet(batch_id, attended_on)
        return self._present(batch, attended_on, sheet)

    def save(self, actor: Actor, scope: BranchScope, payload: SheetSave) -> SheetPublic:
        batch = self._batch(actor, scope, payload.batch_id)
        if limits_to_assigned_batches(actor):
            allowed = set(self.session.scalars(assigned_batch_ids(actor.id)).all())
            if batch.id not in allowed:
                raise AppException(
                    403, "FORBIDDEN", "You can mark attendance only for your own batches"
                )
        enrolled = {student.id: student for _, student in self.repo.active_students(batch.id)}
        unknown = [mark.student_id for mark in payload.marks if mark.student_id not in enrolled]
        if unknown:
            raise AppException(
                422,
                "NOT_ENROLLED",
                "Attendance can be marked only for students with an active seat",
            )
        sheet = self.repo.get_sheet(batch.id, payload.attended_on)
        created = sheet is None
        if sheet is None:
            sheet = AttendanceSheet(
                branch_id=batch.branch_id,
                batch_id=batch.id,
                attended_on=payload.attended_on,
            )
            stamp_new(sheet, actor.id)
            self.session.add(sheet)
            self.session.flush()
        else:
            stamp_update(sheet, actor.id)
        for item in payload.marks:
            existing = self.repo.mark_for(sheet.id, item.student_id)
            if existing is None:
                existing = AttendanceMark(
                    branch_id=batch.branch_id,
                    sheet_id=sheet.id,
                    student_id=item.student_id,
                    status=item.status,
                    note=item.note,
                )
                stamp_new(existing, actor.id)
                self.session.add(existing)
            else:
                existing.status = item.status
                existing.note = item.note
                stamp_update(existing, actor.id)
        self.audit.record(
            action="create" if created else "update",
            entity="attendance_sheet",
            entity_id=sheet.id,
            actor_id=actor.id,
            branch_id=batch.branch_id,
            new_values={
                "batch_id": batch.id,
                "attended_on": payload.attended_on.isoformat(),
                "marks": len(payload.marks),
            },
        )
        commit_or_conflict(self.session)
        return self._present(
            batch, payload.attended_on, self.repo.get_sheet(batch.id, payload.attended_on)
        )

    def _batch(self, actor, scope, batch_id):
        batch = self.batches.get_batch(batch_id, scope, actor)
        if batch is None:
            raise not_found("Batch")
        return batch

    def _present(self, batch, attended_on, sheet) -> SheetPublic:
        saved = {}
        if sheet is not None:
            saved = {mark.student_id: mark for mark in sheet.marks if mark.deleted_at is None}
        rows = []
        for _enrollment, student in self.repo.active_students(batch.id):
            mark = saved.get(student.id)
            rows.append(
                MarkPublic(
                    student_id=student.id,
                    student_name=student.full_name,
                    admission_no=student.admission_no,
                    status=mark.status if mark else None,
                    note=mark.note if mark else None,
                )
            )
        return SheetPublic(
            id=sheet.id if sheet else None,
            batch_id=batch.id,
            batch_name=batch.name,
            attended_on=attended_on,
            marks=rows,
        )
