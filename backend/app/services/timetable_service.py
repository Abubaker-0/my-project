"""Weekly slots. A room or a teacher cannot be in two places at the same time."""

from __future__ import annotations

from datetime import time

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.models.academics import Batch, Room, Staff
from app.models.operations import ClassSession
from app.repositories.operations import TimetableRepository, lock_row
from app.repositories.records import BatchRepository
from app.schemas.common import Page
from app.schemas.operations import SessionCreate, SessionPublic, SessionUpdate
from app.services.audit_service import AuditService
from app.services.guards import not_found, snapshot, stamp_new, stamp_update
from app.services.transactions import commit_or_conflict

_FIELDS = (
    "batch_id",
    "room_id",
    "staff_id",
    "weekday",
    "start_time",
    "end_time",
    "status",
)


class TimetableService:
    """Creates and cancels weekly sessions."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = TimetableRepository(session)
        self.batches = BatchRepository(session)
        self.audit = AuditService(session)

    def list_sessions(
        self, actor: Actor, scope: BranchScope, *, batch_id, page, page_size, order
    ) -> Page[SessionPublic]:
        rows, total = self.repo.list_sessions(
            scope,
            actor,
            batch_id=batch_id,
            offset=(page - 1) * page_size,
            limit=page_size,
            order=order,
        )
        return Page(
            items=[to_session(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_session(
        self, actor: Actor, scope: BranchScope, payload: SessionCreate
    ) -> SessionPublic:
        batch = self._batch(actor, scope, payload.batch_id)
        self._lock_resources(payload.staff_id, payload.room_id)
        self._check_times(payload.start_time, payload.end_time)
        self._check_place(batch, payload.room_id, payload.staff_id)
        self._reject_overlap(
            room_id=payload.room_id,
            staff_id=payload.staff_id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
            starts_on=batch.start_date,
            ends_on=batch.end_date,
            exclude_id=None,
        )
        row = ClassSession(
            branch_id=batch.branch_id,
            batch_id=batch.id,
            room_id=payload.room_id,
            staff_id=payload.staff_id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
            starts_on=batch.start_date,
            ends_on=batch.end_date,
            status="scheduled",
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self.audit.record(
            action="create",
            entity="class_session",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            new_values=snapshot(row, _FIELDS),
        )
        commit_or_conflict(self.session)
        loaded = self.repo.get_session(row.id, scope, actor)
        return to_session(loaded)

    def update_session(
        self, actor: Actor, scope: BranchScope, session_id: int, payload: SessionUpdate
    ) -> SessionPublic:
        row = self.repo.get_session(session_id, scope, actor)
        if row is None or row.status != "scheduled":
            raise not_found("Session")
        before = snapshot(row, _FIELDS)
        room_id = payload.room_id if "room_id" in payload.model_fields_set else row.room_id
        staff_id = payload.staff_id if "staff_id" in payload.model_fields_set else row.staff_id
        weekday = payload.weekday if payload.weekday is not None else row.weekday
        start_time = payload.start_time or row.start_time
        end_time = payload.end_time or row.end_time
        self._lock_resources(staff_id, room_id)
        self._check_times(start_time, end_time)
        self._check_place(row.batch, room_id, staff_id)
        self._reject_overlap(
            room_id=room_id,
            staff_id=staff_id,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            starts_on=row.starts_on,
            ends_on=row.ends_on,
            exclude_id=row.id,
        )
        row.room_id = room_id
        row.staff_id = staff_id
        row.weekday = weekday
        row.start_time = start_time
        row.end_time = end_time
        stamp_update(row, actor.id)
        self.audit.record(
            action="update",
            entity="class_session",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            old_values=before,
            new_values=snapshot(row, _FIELDS),
        )
        commit_or_conflict(self.session)
        return to_session(self.repo.get_session(row.id, scope, actor))

    def cancel_session(self, actor: Actor, scope: BranchScope, session_id: int) -> SessionPublic:
        row = self.repo.get_session(session_id, scope, actor)
        if row is None:
            raise not_found("Session")
        if row.status == "cancelled":
            return to_session(row)
        before = snapshot(row, _FIELDS)
        row.status = "cancelled"
        stamp_update(row, actor.id)
        self.audit.record(
            action="cancel",
            entity="class_session",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            old_values=before,
            new_values=snapshot(row, _FIELDS),
        )
        commit_or_conflict(self.session)
        return to_session(self.repo.get_session(row.id, scope, actor))

    def _batch(self, actor: Actor, scope: BranchScope, batch_id: int) -> Batch:
        batch = self.batches.get_batch(batch_id, scope, actor)
        if batch is None:
            raise not_found("Batch")
        if batch.status not in {"planned", "active"}:
            raise AppException(
                422, "BATCH_CLOSED", "Sessions can be added only to a planned or active batch"
            )
        return batch

    def _lock_resources(self, staff_id: int | None, room_id: int | None) -> None:
        if staff_id is not None:
            if lock_row(self.session, Staff, staff_id) is None:
                raise not_found("Teacher")
        if room_id is not None:
            if lock_row(self.session, Room, room_id) is None:
                raise not_found("Room")

    def _check_times(self, start_time: time, end_time: time) -> None:
        if end_time <= start_time:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "The session must end after it starts",
                details=[{"field": "end_time", "message": "End time is not after the start time"}],
            )

    def _check_place(self, batch: Batch, room_id: int | None, staff_id: int | None) -> None:
        if room_id is None and staff_id is None:
            raise AppException(422, "VALIDATION_ERROR", "Choose a room or a teacher")
        if room_id is not None:
            room = self.session.get(Room, room_id)
            if room is None or room.deleted_at is not None or room.branch_id != batch.branch_id:
                raise not_found("Room")
        if staff_id is not None:
            assigned = {link.staff_id for link in batch.teachers}
            staff = self.session.get(Staff, staff_id)
            if staff is None or staff.deleted_at is not None or staff.branch_id != batch.branch_id:
                raise not_found("Teacher")
            if staff_id not in assigned:
                raise AppException(
                    422, "VALIDATION_ERROR", "That teacher is not assigned to this batch"
                )

    def _reject_overlap(
        self, *, room_id, staff_id, weekday, start_time, end_time, starts_on, ends_on, exclude_id
    ):
        for other in self.repo.conflicts(
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            starts_on=starts_on,
            ends_on=ends_on,
            exclude_id=exclude_id,
        ):
            if room_id is not None and other.room_id == room_id:
                raise AppException(
                    409, "ROOM_OVERLAP", "That room already has a session at this time"
                )
            if staff_id is not None and other.staff_id == staff_id:
                raise AppException(
                    409, "TEACHER_OVERLAP", "That teacher already has a session at this time"
                )


def to_session(row: ClassSession) -> SessionPublic:
    teacher = (
        row.staff.user.full_name if row.staff is not None and row.staff.user is not None else None
    )
    return SessionPublic(
        id=row.id,
        branch_id=row.branch_id,
        batch_id=row.batch_id,
        batch_name=row.batch.name,
        course_name=row.batch.course.name,
        room_id=row.room_id,
        room_name=row.room.name if row.room is not None else None,
        staff_id=row.staff_id,
        teacher_name=teacher,
        weekday=row.weekday,
        start_time=row.start_time,
        end_time=row.end_time,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        status=row.status,
        created_at=row.created_at,
    )
