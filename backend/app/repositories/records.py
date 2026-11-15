"""Queries for calendars, courses, people, and enrollments."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.domain.access import (
    limits_to_assigned_batches,
    limits_to_linked_children,
    limits_to_self,
)
from app.domain.actor import Actor, BranchScope
from app.models.academics import (
    AcademicYear,
    Batch,
    BatchTeacher,
    Course,
    Room,
    Staff,
    Subject,
    Term,
)
from app.models.enrollment import Enrollment
from app.models.people import Guardian, Inquiry, Student, StudentDocument, StudentGuardian
from app.repositories.base import Repository, apply_branch_scope


def lock_by_id(session, model, row_id: int):
    """Load one row, locking it on MariaDB so capacity checks are serial."""
    stmt = select(model).where(model.id == row_id)
    if session.get_bind().dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def assigned_batch_ids(user_id: int):
    """Batches where this user is an active staff member."""
    return (
        select(BatchTeacher.batch_id)
        .join(Staff, Staff.id == BatchTeacher.staff_id)
        .where(
            Staff.user_id == user_id,
            Staff.deleted_at.is_(None),
            Staff.status == "active",
        )
    )


def _assigned_student_ids(user_id: int):
    return (
        select(Enrollment.student_id)
        .join(Batch, Batch.id == Enrollment.batch_id)
        .where(
            Enrollment.batch_id.in_(assigned_batch_ids(user_id)),
            Enrollment.deleted_at.is_(None),
            Enrollment.status.in_(("active", "waitlisted", "completed")),
            Batch.deleted_at.is_(None),
        )
    )


class CalendarRepository(Repository):
    """Academic years and terms."""

    def list_years(self, scope: BranchScope, *, q: str | None, offset: int, limit: int, order):
        stmt = select(AcademicYear).where(AcademicYear.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, AcademicYear.branch_id, scope)
        if q:
            stmt = stmt.where(AcademicYear.name.ilike(f"%{q}%"))
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_year(self, year_id: int, scope: BranchScope) -> AcademicYear | None:
        cached = self.session.get(AcademicYear, year_id)
        if cached is not None:
            self.session.expire(cached, ["terms"])
        stmt = (
            select(AcademicYear)
            .options(selectinload(AcademicYear.terms))
            .where(AcademicYear.id == year_id, AcademicYear.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, AcademicYear.branch_id, scope)
        return self.session.scalar(stmt)

    def clear_current(self, branch_id: int, keep_id: int | None) -> None:
        stmt = select(AcademicYear).where(
            AcademicYear.branch_id == branch_id,
            AcademicYear.deleted_at.is_(None),
            AcademicYear.is_current.is_(True),
        )
        for row in self.session.scalars(stmt):
            if row.id != keep_id:
                row.is_current = False

    def get_term(self, term_id: int, scope: BranchScope) -> Term | None:
        stmt = select(Term).where(Term.id == term_id, Term.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Term.branch_id, scope)
        return self.session.scalar(stmt)


class RoomRepository(Repository):
    """Classrooms."""

    def list_rooms(self, scope: BranchScope, *, q: str | None, offset: int, limit: int, order):
        stmt = select(Room).where(Room.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Room.branch_id, scope)
        if q:
            stmt = stmt.where(Room.name.ilike(f"%{q}%"))
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_room(self, room_id: int, scope: BranchScope) -> Room | None:
        stmt = select(Room).where(Room.id == room_id, Room.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Room.branch_id, scope)
        return self.session.scalar(stmt)

    def name_taken(self, branch_id: int, name: str, exclude_id: int | None) -> bool:
        stmt = select(Room.id).where(
            Room.branch_id == branch_id,
            Room.deleted_at.is_(None),
            func.lower(Room.name) == name.lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(Room.id != exclude_id)
        return self.session.scalar(stmt) is not None


class CourseRepository(Repository):
    """Subjects and courses."""

    def list_subjects(self, scope: BranchScope, *, q: str | None, offset: int, limit: int, order):
        stmt = select(Subject).where(Subject.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Subject.branch_id, scope)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Subject.name.ilike(like), Subject.code.ilike(like)))
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_subject(self, subject_id: int, scope: BranchScope) -> Subject | None:
        stmt = select(Subject).where(Subject.id == subject_id, Subject.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Subject.branch_id, scope)
        return self.session.scalar(stmt)

    def code_taken(self, branch_id: int, code: str, exclude_id: int | None) -> bool:
        stmt = select(Subject.id).where(
            Subject.branch_id == branch_id,
            Subject.deleted_at.is_(None),
            func.lower(Subject.code) == code.lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(Subject.id != exclude_id)
        return self.session.scalar(stmt) is not None

    def list_courses(
        self, scope: BranchScope, actor: Actor, *, q: str | None, offset: int, limit: int, order
    ):
        stmt = (
            select(Course).options(selectinload(Course.subject)).where(Course.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Course.branch_id, scope)
        stmt = self._teacher_courses(stmt, actor)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Course.name.ilike(like), Course.level.ilike(like)))
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_course(self, course_id: int, scope: BranchScope, actor: Actor) -> Course | None:
        stmt = (
            select(Course)
            .options(selectinload(Course.subject))
            .where(Course.id == course_id, Course.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Course.branch_id, scope)
        stmt = self._teacher_courses(stmt, actor)
        return self.session.scalar(stmt)

    def _teacher_courses(self, stmt, actor: Actor):
        if not limits_to_assigned_batches(actor):
            return stmt
        course_ids = select(Batch.course_id).where(
            Batch.id.in_(assigned_batch_ids(actor.id)),
            Batch.deleted_at.is_(None),
        )
        return stmt.where(Course.id.in_(course_ids))


class BatchRepository(Repository):
    """Batches, teacher assignments, and seat counts."""

    def list_batches(
        self, scope: BranchScope, actor: Actor, *, q: str | None, offset: int, limit: int, order
    ):
        stmt = (
            select(Batch)
            .options(selectinload(Batch.course), selectinload(Batch.term), selectinload(Batch.room))
            .where(Batch.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Batch.branch_id, scope)
        stmt = self._teacher_batches(stmt, actor)
        if q:
            stmt = stmt.where(Batch.name.ilike(f"%{q}%"))
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_batch(self, batch_id: int, scope: BranchScope, actor: Actor) -> Batch | None:
        cached = self.session.get(Batch, batch_id)
        if cached is not None:
            self.session.expire(cached, ["teachers"])
        stmt = (
            select(Batch)
            .options(
                selectinload(Batch.course),
                selectinload(Batch.term),
                selectinload(Batch.room),
                selectinload(Batch.teachers)
                .selectinload(BatchTeacher.staff)
                .selectinload(Staff.user),
            )
            .where(Batch.id == batch_id, Batch.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Batch.branch_id, scope)
        stmt = self._teacher_batches(stmt, actor)
        return self.session.scalar(stmt)

    def counts(self, batch_ids: list[int]) -> dict[int, dict[str, int]]:
        """Return active and waitlisted totals for the given batches in one query."""
        found = {batch_id: {"active": 0, "waitlisted": 0} for batch_id in batch_ids}
        if not batch_ids:
            return found
        rows = self.session.execute(
            select(Enrollment.batch_id, Enrollment.status, func.count())
            .where(
                Enrollment.batch_id.in_(batch_ids),
                Enrollment.deleted_at.is_(None),
                Enrollment.status.in_(("active", "waitlisted")),
            )
            .group_by(Enrollment.batch_id, Enrollment.status)
        ).all()
        for batch_id, status, count in rows:
            found[batch_id][status] = int(count)
        return found

    def count_active(self, batch_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Enrollment)
            .where(
                Enrollment.batch_id == batch_id,
                Enrollment.status == "active",
                Enrollment.deleted_at.is_(None),
            )
        )
        return int(self.session.scalar(stmt) or 0)

    def next_waitlist_position(self, batch_id: int) -> int:
        stmt = select(func.max(Enrollment.waitlist_position)).where(
            Enrollment.batch_id == batch_id,
            Enrollment.status == "waitlisted",
            Enrollment.deleted_at.is_(None),
        )
        current = self.session.scalar(stmt) or 0
        return int(current) + 1

    def first_waitlisted(self, batch_id: int) -> Enrollment | None:
        stmt = (
            select(Enrollment)
            .where(
                Enrollment.batch_id == batch_id,
                Enrollment.status == "waitlisted",
                Enrollment.deleted_at.is_(None),
            )
            .order_by(Enrollment.waitlist_position.asc(), Enrollment.id.asc())
        )
        if self.session.get_bind().dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def open_enrollment(self, student_id: int, batch_id: int) -> Enrollment | None:
        stmt = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.batch_id == batch_id,
            Enrollment.deleted_at.is_(None),
            Enrollment.status.in_(("active", "waitlisted")),
        )
        return self.session.scalar(stmt)

    def open_for_student(self, student_id: int) -> list[Enrollment]:
        stmt = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.deleted_at.is_(None),
            Enrollment.status.in_(("active", "waitlisted")),
        )
        return list(self.session.scalars(stmt).all())

    def staff_for_user(self, branch_id: int, user_id: int) -> Staff | None:
        stmt = select(Staff).where(
            Staff.branch_id == branch_id,
            Staff.user_id == user_id,
            Staff.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def primary_teacher(self, batch_id: int) -> BatchTeacher | None:
        stmt = select(BatchTeacher).where(
            BatchTeacher.batch_id == batch_id,
            BatchTeacher.role == "primary",
        )
        return self.session.scalar(stmt)

    def assignment(self, batch_id: int, staff_id: int) -> BatchTeacher | None:
        stmt = select(BatchTeacher).where(
            BatchTeacher.batch_id == batch_id,
            BatchTeacher.staff_id == staff_id,
        )
        return self.session.scalar(stmt)

    def _teacher_batches(self, stmt, actor: Actor):
        if not limits_to_assigned_batches(actor):
            return stmt
        return stmt.where(Batch.id.in_(assigned_batch_ids(actor.id)))


class StudentRepository(Repository):
    """Students and the guardians and documents attached to them."""

    def list_students(
        self,
        scope: BranchScope,
        actor: Actor,
        *,
        q: str | None,
        status: str | None,
        offset: int,
        limit: int,
        order,
    ):
        stmt = select(Student).where(Student.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Student.branch_id, scope)
        stmt = self._owned(stmt, actor)
        if status:
            stmt = stmt.where(Student.status == status)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Student.first_name.ilike(like),
                    Student.last_name.ilike(like),
                    Student.admission_no.ilike(like),
                    Student.grade_level.ilike(like),
                )
            )
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_student(self, student_id: int, scope: BranchScope, actor: Actor) -> Student | None:
        cached = self.session.get(Student, student_id)
        if cached is not None:
            self.session.expire(cached, ["guardian_links", "documents"])
        stmt = (
            select(Student)
            .options(
                selectinload(Student.guardian_links).selectinload(StudentGuardian.guardian),
                selectinload(Student.documents),
            )
            .where(Student.id == student_id, Student.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Student.branch_id, scope)
        stmt = self._owned(stmt, actor)
        student = self.session.scalar(stmt)
        if student is not None:
            student.documents = [doc for doc in student.documents if doc.deleted_at is None]
        return student

    def get_guardian(self, guardian_id: int, scope: BranchScope) -> Guardian | None:
        stmt = select(Guardian).where(Guardian.id == guardian_id, Guardian.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Guardian.branch_id, scope)
        return self.session.scalar(stmt)

    def link(self, student_id: int, guardian_id: int) -> StudentGuardian | None:
        stmt = select(StudentGuardian).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.guardian_id == guardian_id,
        )
        return self.session.scalar(stmt)

    def document(self, document_id: int, student_id: int) -> StudentDocument | None:
        stmt = select(StudentDocument).where(
            StudentDocument.id == document_id,
            StudentDocument.student_id == student_id,
            StudentDocument.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def _owned(self, stmt, actor: Actor):
        clauses = []
        if limits_to_assigned_batches(actor):
            clauses.append(Student.id.in_(_assigned_student_ids(actor.id)))
        if limits_to_linked_children(actor):
            linked = (
                select(StudentGuardian.student_id)
                .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
                .where(Guardian.user_id == actor.id, Guardian.deleted_at.is_(None))
            )
            clauses.append(Student.id.in_(linked))
        if limits_to_self(actor):
            clauses.append(Student.user_id == actor.id)
        if not clauses:
            return stmt
        if len(clauses) == 1:
            return stmt.where(clauses[0])
        return stmt.where(or_(*clauses))


class InquiryRepository(Repository):
    """Leads and their follow-up notes."""

    def list_inquiries(
        self,
        scope: BranchScope,
        *,
        q: str | None,
        status: str | None,
        offset: int,
        limit: int,
        order,
    ):
        stmt = (
            select(Inquiry)
            .options(selectinload(Inquiry.course))
            .where(Inquiry.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Inquiry.branch_id, scope)
        if status:
            stmt = stmt.where(Inquiry.status == status)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(Inquiry.name.ilike(like), Inquiry.phone.ilike(like), Inquiry.email.ilike(like))
            )
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_inquiry(self, inquiry_id: int, scope: BranchScope) -> Inquiry | None:
        cached = self.session.get(Inquiry, inquiry_id)
        if cached is not None:
            self.session.expire(cached, ["followups"])
        stmt = (
            select(Inquiry)
            .options(selectinload(Inquiry.course), selectinload(Inquiry.followups))
            .where(Inquiry.id == inquiry_id, Inquiry.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Inquiry.branch_id, scope)
        return self.session.scalar(stmt)


class EnrollmentRepository(Repository):
    """Enrollment lists. Capacity changes live on BatchRepository under a lock."""

    def list_enrollments(
        self,
        scope: BranchScope,
        actor: Actor,
        *,
        batch_id: int | None,
        student_id: int | None,
        status: str | None,
        offset: int,
        limit: int,
        order,
    ):
        stmt = (
            select(Enrollment)
            .options(
                selectinload(Enrollment.student),
                selectinload(Enrollment.batch).selectinload(Batch.course),
            )
            .where(Enrollment.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Enrollment.branch_id, scope)
        stmt = _enrollment_owner(stmt, actor)
        if batch_id is not None:
            stmt = stmt.where(Enrollment.batch_id == batch_id)
        if student_id is not None:
            stmt = stmt.where(Enrollment.student_id == student_id)
        if status:
            stmt = stmt.where(Enrollment.status == status)
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_enrollment(
        self, enrollment_id: int, scope: BranchScope, actor: Actor
    ) -> Enrollment | None:
        stmt = (
            select(Enrollment)
            .options(
                selectinload(Enrollment.student),
                selectinload(Enrollment.batch).selectinload(Batch.course),
            )
            .where(Enrollment.id == enrollment_id, Enrollment.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Enrollment.branch_id, scope)
        stmt = _enrollment_owner(stmt, actor)
        return self.session.scalar(stmt)


def _enrollment_owner(stmt, actor: Actor):
    """Teachers see their batches. Parents and students see their own people."""
    filters = []
    if limits_to_assigned_batches(actor):
        filters.append(Enrollment.batch_id.in_(assigned_batch_ids(actor.id)))
    family = []
    if limits_to_linked_children(actor):
        linked = (
            select(StudentGuardian.student_id)
            .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
            .where(Guardian.user_id == actor.id, Guardian.deleted_at.is_(None))
        )
        family.append(Enrollment.student_id.in_(linked))
    if limits_to_self(actor):
        own = select(Student.id).where(Student.user_id == actor.id, Student.deleted_at.is_(None))
        family.append(Enrollment.student_id.in_(own))
    if family:
        filters.append(or_(*family) if len(family) > 1 else family[0])
    if not filters:
        return stmt
    if len(filters) == 1:
        return stmt.where(filters[0])
    return stmt.where(or_(*filters))
