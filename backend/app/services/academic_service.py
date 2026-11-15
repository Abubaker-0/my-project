"""Subjects, courses, batches, and teacher assignment."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.models.academics import Batch, BatchTeacher, Course, Room, Staff, Subject, Term
from app.models.branch import Branch
from app.repositories.branch_repository import BranchRepository
from app.repositories.records import BatchRepository, CourseRepository, RoomRepository, lock_by_id
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.records import (
    BatchCreate,
    BatchDetail,
    BatchPublic,
    BatchTeacherCreate,
    BatchTeacherPublic,
    BatchUpdate,
    CourseCreate,
    CoursePublic,
    CourseUpdate,
    SubjectCreate,
    SubjectPublic,
    SubjectUpdate,
)
from app.services.audit_service import AuditService
from app.services.enrollment_service import EnrollmentService
from app.services.guards import (
    ensure_branch,
    not_found,
    require_order,
    snapshot,
    soft_delete,
    stamp_new,
    stamp_update,
)
from app.services.numbering import NumberingService
from app.services.transactions import commit_or_conflict


class AcademicService:
    """Owns the catalog of subjects, courses, and the batches that have seats."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.batches = BatchRepository(session)
        self.rooms = RoomRepository(session)
        self.branches = BranchRepository(session)
        self.users = UserRepository(session)
        self.numbers = NumberingService(session)
        self.audit = AuditService(session)

    def list_subjects(self, scope, *, q, page, page_size, order) -> Page[SubjectPublic]:
        """Return one page of subjects."""
        rows, total = self.courses.list_subjects(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[_subject(row) for row in rows], total=total, page=page, page_size=page_size
        )

    def create_subject(
        self, actor: Actor, scope: BranchScope, payload: SubjectCreate
    ) -> SubjectPublic:
        """Add a subject code for one campus."""
        ensure_branch(scope, payload.branch_id)
        code = payload.code.strip().upper()
        if self.courses.code_taken(payload.branch_id, code, None):
            raise AppException(409, "CONFLICT", "That subject code is already used at this campus")
        row = Subject(
            branch_id=payload.branch_id, code=code, name=payload.name.strip(), status="active"
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self._audit(
            actor, "create", "subject", row.id, row.branch_id, None, snapshot(row, ("code", "name"))
        )
        commit_or_conflict(self.session)
        return _subject(row)

    def update_subject(
        self, actor, scope, subject_id: int, payload: SubjectUpdate
    ) -> SubjectPublic:
        """Rename a subject or change its code."""
        row = self.courses.get_subject(subject_id, scope)
        if row is None:
            raise not_found("Subject")
        old = snapshot(row, ("code", "name", "status"))
        if payload.code is not None:
            code = payload.code.strip().upper()
            if self.courses.code_taken(row.branch_id, code, row.id):
                raise AppException(
                    409, "CONFLICT", "That subject code is already used at this campus"
                )
            row.code = code
        if payload.name is not None:
            row.name = payload.name.strip()
        if payload.status is not None:
            row.status = payload.status
        stamp_update(row, actor.id)
        self._audit(
            actor,
            "update",
            "subject",
            row.id,
            row.branch_id,
            old,
            snapshot(row, ("code", "name", "status")),
        )
        commit_or_conflict(self.session)
        return _subject(row)

    def delete_subject(self, actor, scope, subject_id: int) -> None:
        """Archive a subject that no active course still uses."""
        row = self.courses.get_subject(subject_id, scope)
        if row is None:
            raise not_found("Subject")
        used = self.session.scalar(
            select(Course.id).where(Course.subject_id == row.id, Course.deleted_at.is_(None))
        )
        if used is not None:
            raise AppException(409, "CONFLICT", "Archive the courses in this subject first")
        soft_delete(row, actor.id)
        self._audit(actor, "delete", "subject", row.id, row.branch_id, {"code": row.code}, None)
        commit_or_conflict(self.session)

    def list_courses(self, actor, scope, *, q, page, page_size, order) -> Page[CoursePublic]:
        """Return one page of courses. Teachers see courses for their batches only."""
        rows, total = self.courses.list_courses(
            scope, actor, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[_course(row) for row in rows], total=total, page=page, page_size=page_size
        )

    def get_course(self, actor, scope, course_id: int) -> CoursePublic:
        """Return one course."""
        row = self.courses.get_course(course_id, scope, actor)
        if row is None:
            raise not_found("Course")
        return _course(row)

    def create_course(self, actor, scope, payload: CourseCreate) -> CoursePublic:
        """Offer a subject at a level."""
        ensure_branch(scope, payload.branch_id)
        subject = self.courses.get_subject(payload.subject_id, scope)
        if subject is None or subject.branch_id != payload.branch_id:
            raise not_found("Subject")
        row = Course(
            branch_id=payload.branch_id,
            subject_id=subject.id,
            name=payload.name.strip(),
            level=payload.level.strip(),
            description=_text(payload.description),
            duration_weeks=payload.duration_weeks,
            status=payload.status,
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        row.subject = subject
        self._audit(
            actor,
            "create",
            "course",
            row.id,
            row.branch_id,
            None,
            snapshot(row, ("name", "level", "status")),
        )
        commit_or_conflict(self.session)
        return _course(row)

    def update_course(self, actor, scope, course_id: int, payload: CourseUpdate) -> CoursePublic:
        """Update a course. The subject, when changed, must belong to the same campus."""
        row = self.courses.get_course(course_id, scope, actor)
        if row is None:
            raise not_found("Course")
        old = snapshot(row, ("name", "level", "status", "duration_weeks", "subject_id"))
        if payload.subject_id is not None:
            subject = self.courses.get_subject(payload.subject_id, scope)
            if subject is None or subject.branch_id != row.branch_id:
                raise not_found("Subject")
            row.subject_id = subject.id
            row.subject = subject
        if payload.name is not None:
            row.name = payload.name.strip()
        if payload.level is not None:
            row.level = payload.level.strip()
        if "description" in payload.model_fields_set:
            row.description = _text(payload.description)
        if payload.duration_weeks is not None:
            row.duration_weeks = payload.duration_weeks
        if payload.status is not None:
            row.status = payload.status
        stamp_update(row, actor.id)
        self._audit(
            actor,
            "update",
            "course",
            row.id,
            row.branch_id,
            old,
            snapshot(row, ("name", "level", "status")),
        )
        commit_or_conflict(self.session)
        return _course(self.courses.get_course(row.id, scope, actor))

    def delete_course(self, actor, scope, course_id: int) -> None:
        """Archive a course that has no open batch."""
        row = self.courses.get_course(course_id, scope, actor)
        if row is None:
            raise not_found("Course")
        batch = self.session.scalar(
            select(Batch.id).where(Batch.course_id == row.id, Batch.deleted_at.is_(None))
        )
        if batch is not None:
            raise AppException(409, "CONFLICT", "Archive the batches for this course first")
        soft_delete(row, actor.id)
        self._audit(actor, "delete", "course", row.id, row.branch_id, {"name": row.name}, None)
        commit_or_conflict(self.session)

    def list_batches(self, actor, scope, *, q, page, page_size, order) -> Page[BatchPublic]:
        """Return one page of batches with seat counts. Teachers see their own batches."""
        rows, total = self.batches.list_batches(
            scope, actor, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        counts = self.batches.counts([row.id for row in rows])
        return Page(
            items=[_batch(row, counts) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_batch(self, actor, scope, batch_id: int) -> BatchDetail:
        """Return one batch, its teachers, and its seat counts."""
        row = self._batch(actor, scope, batch_id)
        counts = self.batches.counts([row.id])
        return _batch_detail(row, counts)

    def create_batch(self, actor, scope, payload: BatchCreate) -> BatchDetail:
        """Open a batch. Its dates must sit inside the term."""
        ensure_branch(scope, payload.branch_id)
        course = self.courses.get_course(payload.course_id, scope, actor)
        if course is None or course.branch_id != payload.branch_id:
            raise not_found("Course")
        term = self.session.get(Term, payload.term_id)
        if term is None or term.deleted_at is not None or term.branch_id != payload.branch_id:
            raise not_found("Term")
        require_order(payload.start_date, payload.end_date, "end_date")
        if payload.start_date < term.start_date or payload.end_date > term.end_date:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Batch dates must fall inside the term",
                details=[{"field": "start_date", "message": "Keep the batch inside the term"}],
            )
        room = self._room(scope, payload.room_id, payload.branch_id)
        row = Batch(
            branch_id=payload.branch_id,
            course_id=course.id,
            term_id=term.id,
            room_id=room.id if room else None,
            name=payload.name.strip(),
            start_date=payload.start_date,
            end_date=payload.end_date,
            capacity=payload.capacity,
            status=payload.status,
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self._audit(
            actor,
            "create",
            "batch",
            row.id,
            row.branch_id,
            None,
            snapshot(row, ("name", "capacity", "status")),
        )
        commit_or_conflict(self.session)
        return self.get_batch(actor, scope, row.id)

    def update_batch(self, actor, scope, batch_id: int, payload: BatchUpdate) -> BatchDetail:
        """Update a batch. Capacity cannot drop below the number of active seats.

        Raising capacity promotes waitlisted students until the new limit is full.
        """
        row = lock_by_id(self.session, Batch, batch_id)
        visible = self._batch(actor, scope, batch_id)
        if row is None or visible is None:
            raise not_found("Batch")
        old = snapshot(row, ("name", "capacity", "status", "room_id"))
        if payload.name is not None:
            row.name = payload.name.strip()
        if "room_id" in payload.model_fields_set:
            room = self._room(scope, payload.room_id, row.branch_id)
            row.room_id = room.id if room else None
        start = payload.start_date or row.start_date
        end = payload.end_date or row.end_date
        require_order(start, end, "end_date")
        term = self.session.get(Term, row.term_id)
        if term is not None and (start < term.start_date or end > term.end_date):
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Batch dates must fall inside the term",
                details=[{"field": "start_date", "message": "Keep the batch inside the term"}],
            )
        row.start_date = start
        row.end_date = end
        if payload.capacity is not None:
            active = self.batches.count_active(row.id)
            if payload.capacity < active:
                raise AppException(
                    422,
                    "VALIDATION_ERROR",
                    "Capacity cannot be lower than the number of active students",
                    details=[
                        {"field": "capacity", "message": f"{active} students are already seated"}
                    ],
                )
            row.capacity = payload.capacity
        if payload.status is not None:
            row.status = payload.status
        stamp_update(row, actor.id)
        if payload.capacity is not None and row.status in {"planned", "active"}:
            EnrollmentService(self.session).fill_open_seats(actor, row)
        self._audit(
            actor,
            "update",
            "batch",
            row.id,
            row.branch_id,
            old,
            snapshot(row, ("name", "capacity", "status")),
        )
        commit_or_conflict(self.session)
        return self.get_batch(actor, scope, row.id)

    def delete_batch(self, actor, scope, batch_id: int) -> None:
        """Archive a batch that has no open seats."""
        row = self._batch(actor, scope, batch_id)
        counts = self.batches.counts([row.id])[row.id]
        if counts["active"] or counts["waitlisted"]:
            raise AppException(
                409, "CONFLICT", "Withdraw the open seats before archiving this batch"
            )
        soft_delete(row, actor.id)
        self._audit(actor, "delete", "batch", row.id, row.branch_id, {"name": row.name}, None)
        commit_or_conflict(self.session)

    def assign_teacher(
        self, actor, scope, batch_id: int, payload: BatchTeacherCreate
    ) -> BatchDetail:
        """Assign a teacher. A batch has one primary teacher."""
        batch = self._batch(actor, scope, batch_id)
        user = self.users.get(payload.user_id)
        if user is None or user.status != "active":
            raise not_found("User")
        if not _teaches(user, batch.branch_id):
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "That account is not a teacher at this campus",
                details=[{"field": "user_id", "message": "Choose a teacher for this campus"}],
            )
        staff = self.batches.staff_for_user(batch.branch_id, user.id)
        if staff is None:
            branch = self.session.get(Branch, batch.branch_id)
            employee_no = self.numbers.allocate(
                batch.branch_id, "employee", f"{branch.code}-EMP-", actor.id
            )
            staff = Staff(
                branch_id=batch.branch_id,
                user_id=user.id,
                employee_no=employee_no,
                designation="Teacher",
                status="active",
            )
            stamp_new(staff, actor.id)
            self.session.add(staff)
            self.session.flush()
        existing = self.batches.assignment(batch.id, staff.id)
        if payload.role == "primary":
            current = self.batches.primary_teacher(batch.id)
            if current is not None and current.staff_id != staff.id:
                raise AppException(409, "CONFLICT", "This batch already has a primary teacher")
        if existing is None:
            existing = BatchTeacher(
                batch_id=batch.id, staff_id=staff.id, role=payload.role, created_by=actor.id
            )
            self.session.add(existing)
        else:
            existing.role = payload.role
        self.session.flush()
        self._audit(
            actor,
            "update",
            "batch",
            batch.id,
            batch.branch_id,
            None,
            {"teacher_user_id": user.id, "role": payload.role},
        )
        commit_or_conflict(self.session)
        return self.get_batch(actor, scope, batch.id)

    def remove_teacher(self, actor, scope, batch_id: int, staff_id: int) -> BatchDetail:
        """Remove a teacher assignment. The staff profile stays."""
        batch = self._batch(actor, scope, batch_id)
        assignment = self.batches.assignment(batch.id, staff_id)
        if assignment is None:
            raise not_found("Teacher")
        self.session.delete(assignment)
        self._audit(
            actor, "update", "batch", batch.id, batch.branch_id, {"staff_id": staff_id}, None
        )
        commit_or_conflict(self.session)
        return self.get_batch(actor, scope, batch.id)

    def _batch(self, actor, scope, batch_id: int) -> Batch:
        row = self.batches.get_batch(batch_id, scope, actor)
        if row is None:
            raise not_found("Batch")
        return row

    def _room(self, scope, room_id: int | None, branch_id: int) -> Room | None:
        if room_id is None:
            return None
        room = self.rooms.get_room(room_id, scope)
        if room is None or room.branch_id != branch_id or room.status != "active":
            raise not_found("Room")
        return room

    def _audit(self, actor, action, entity, entity_id, branch_id, old, new) -> None:
        self.audit.record(
            action=action,
            entity=entity,
            entity_id=entity_id,
            actor_id=actor.id,
            branch_id=branch_id,
            old_values=old,
            new_values=new,
        )


def _teaches(user, branch_id: int) -> bool:
    for link in user.role_links:
        role = link.role
        if role.deleted_at is not None or role.name != "teacher":
            continue
        if link.branch_id is None or link.branch_id == branch_id:
            return True
    return False


def _subject(row: Subject) -> SubjectPublic:
    return SubjectPublic(
        id=row.id, branch_id=row.branch_id, code=row.code, name=row.name, status=row.status
    )


def _course(row: Course) -> CoursePublic:
    return CoursePublic(
        id=row.id,
        branch_id=row.branch_id,
        subject_id=row.subject_id,
        subject_name=row.subject.name,
        name=row.name,
        level=row.level,
        description=row.description,
        duration_weeks=row.duration_weeks,
        status=row.status,
        created_at=row.created_at,
    )


def _batch(row: Batch, counts: dict) -> BatchPublic:
    tally = counts.get(row.id, {"active": 0, "waitlisted": 0})
    return BatchPublic(
        id=row.id,
        branch_id=row.branch_id,
        course_id=row.course_id,
        course_name=row.course.name,
        term_id=row.term_id,
        term_name=row.term.name,
        room_id=row.room_id,
        room_name=row.room.name if row.room is not None else None,
        name=row.name,
        start_date=row.start_date,
        end_date=row.end_date,
        capacity=row.capacity,
        status=row.status,
        active_count=tally["active"],
        waitlist_count=tally["waitlisted"],
        created_at=row.created_at,
    )


def _batch_detail(row: Batch, counts: dict) -> BatchDetail:
    base = _batch(row, counts).model_dump()
    teachers = [
        BatchTeacherPublic(
            staff_id=link.staff_id,
            user_id=link.staff.user_id,
            full_name=link.staff.user.full_name,
            employee_no=link.staff.employee_no,
            role=link.role,
        )
        for link in row.teachers
    ]
    return BatchDetail(**base, teachers=teachers)


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
