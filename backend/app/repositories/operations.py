"""Queries for sessions, registers, invoices, and payments."""

from __future__ import annotations

from datetime import date, time

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.domain.access import (
    limits_to_assigned_batches,
    limits_to_linked_children,
    limits_to_self,
)
from app.domain.actor import Actor, BranchScope
from app.models.academics import Batch, Staff
from app.models.enrollment import Enrollment
from app.models.operations import (
    AttendanceMark,
    AttendanceSheet,
    ClassSession,
    FeePlan,
    Invoice,
    Payment,
)
from app.models.people import Guardian, Student, StudentGuardian
from app.repositories.base import Repository, apply_branch_scope
from app.repositories.records import assigned_batch_ids, lock_by_id


def _linked_student_ids(user_id: int):
    return (
        select(StudentGuardian.student_id)
        .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
        .where(Guardian.user_id == user_id, Guardian.deleted_at.is_(None))
    )


class TimetableRepository(Repository):
    """Weekly slots, limited to a teacher's batches when that role applies."""

    def list_sessions(
        self,
        scope: BranchScope,
        actor: Actor,
        *,
        batch_id: int | None,
        offset: int,
        limit: int,
        order,
    ):
        stmt = (
            select(ClassSession)
            .options(
                selectinload(ClassSession.batch).selectinload(Batch.course),
                selectinload(ClassSession.room),
                selectinload(ClassSession.staff).selectinload(Staff.user),
            )
            .where(ClassSession.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, ClassSession.branch_id, scope)
        stmt = self._teacher_batches(stmt, actor)
        if batch_id is not None:
            stmt = stmt.where(ClassSession.batch_id == batch_id)
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_session(self, session_id: int, scope: BranchScope, actor: Actor) -> ClassSession | None:
        stmt = (
            select(ClassSession)
            .options(
                selectinload(ClassSession.batch).selectinload(Batch.course),
                selectinload(ClassSession.room),
                selectinload(ClassSession.staff).selectinload(Staff.user),
            )
            .where(ClassSession.id == session_id, ClassSession.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, ClassSession.branch_id, scope)
        stmt = self._teacher_batches(stmt, actor)
        return self.session.scalar(stmt)

    def conflicts(
        self,
        *,
        weekday: int,
        start_time: time,
        end_time: time,
        starts_on: date,
        ends_on: date,
        exclude_id: int | None,
    ) -> list[ClassSession]:
        """Scheduled slots whose clock time and date range meet this one."""
        stmt = select(ClassSession).where(
            ClassSession.deleted_at.is_(None),
            ClassSession.status == "scheduled",
            ClassSession.weekday == weekday,
            ClassSession.start_time < end_time,
            ClassSession.end_time > start_time,
            ClassSession.starts_on <= ends_on,
            ClassSession.ends_on >= starts_on,
        )
        if exclude_id is not None:
            stmt = stmt.where(ClassSession.id != exclude_id)
        if self.session.get_bind().dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        return list(self.session.scalars(stmt).all())

    def sessions_on(self, scope: BranchScope, actor: Actor, weekday: int, day: date):
        stmt = (
            select(ClassSession)
            .options(
                selectinload(ClassSession.batch),
                selectinload(ClassSession.room),
                selectinload(ClassSession.staff).selectinload(Staff.user),
            )
            .where(
                ClassSession.deleted_at.is_(None),
                ClassSession.status == "scheduled",
                ClassSession.weekday == weekday,
                ClassSession.starts_on <= day,
                ClassSession.ends_on >= day,
            )
        )
        stmt = apply_branch_scope(stmt, ClassSession.branch_id, scope)
        stmt = self._teacher_batches(stmt, actor)
        return list(self.session.scalars(stmt.order_by(ClassSession.start_time)).all())

    def _teacher_batches(self, stmt, actor: Actor):
        if not limits_to_assigned_batches(actor):
            return stmt
        return stmt.where(ClassSession.batch_id.in_(assigned_batch_ids(actor.id)))


class AttendanceRepository(Repository):
    """Registers and the active students who belong on them."""

    def get_sheet(self, batch_id: int, attended_on: date) -> AttendanceSheet | None:
        stmt = (
            select(AttendanceSheet)
            .options(selectinload(AttendanceSheet.marks), selectinload(AttendanceSheet.batch))
            .where(
                AttendanceSheet.batch_id == batch_id,
                AttendanceSheet.attended_on == attended_on,
                AttendanceSheet.deleted_at.is_(None),
            )
        )
        return self.session.scalar(stmt)

    def active_students(self, batch_id: int) -> list[tuple[Enrollment, Student]]:
        stmt = (
            select(Enrollment, Student)
            .join(Student, Student.id == Enrollment.student_id)
            .where(
                Enrollment.batch_id == batch_id,
                Enrollment.status == "active",
                Enrollment.deleted_at.is_(None),
                Student.deleted_at.is_(None),
            )
            .order_by(Student.admission_no)
        )
        return list(self.session.execute(stmt).all())

    def mark_for(self, sheet_id: int, student_id: int) -> AttendanceMark | None:
        return self.session.scalar(
            select(AttendanceMark).where(
                AttendanceMark.sheet_id == sheet_id,
                AttendanceMark.student_id == student_id,
                AttendanceMark.deleted_at.is_(None),
            )
        )

    def sheet_exists(self, batch_id: int, attended_on: date) -> bool:
        stmt = select(AttendanceSheet.id).where(
            AttendanceSheet.batch_id == batch_id,
            AttendanceSheet.attended_on == attended_on,
            AttendanceSheet.deleted_at.is_(None),
        )
        return self.session.scalar(stmt) is not None


class BillingRepository(Repository):
    """Fee plans, invoices, and payments, with parent and student row limits."""

    def list_plans(self, scope: BranchScope, *, q: str | None, offset: int, limit: int, order):
        stmt = select(FeePlan).where(FeePlan.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, FeePlan.branch_id, scope)
        if q:
            stmt = stmt.where(FeePlan.name.ilike(f"%{q}%"))
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_plan(self, plan_id: int, scope: BranchScope) -> FeePlan | None:
        stmt = select(FeePlan).where(FeePlan.id == plan_id, FeePlan.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, FeePlan.branch_id, scope)
        return self.session.scalar(stmt)

    def list_invoices(
        self,
        scope: BranchScope,
        actor: Actor,
        *,
        q: str | None,
        status: str | None,
        student_id: int | None,
        offset: int,
        limit: int,
        order,
    ):
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.student), selectinload(Invoice.payments))
            .where(Invoice.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Invoice.branch_id, scope)
        stmt = self._family(stmt, actor)
        if status:
            stmt = stmt.where(Invoice.status == status)
        if student_id is not None:
            stmt = stmt.where(Invoice.student_id == student_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.join(Student, Student.id == Invoice.student_id).where(
                or_(
                    Invoice.invoice_no.ilike(like),
                    Student.first_name.ilike(like),
                    Student.last_name.ilike(like),
                    Student.admission_no.ilike(like),
                )
            )
        return self.paginate(stmt.order_by(order), offset=offset, limit=limit)

    def get_invoice(self, invoice_id: int, scope: BranchScope, actor: Actor) -> Invoice | None:
        cached = self.session.get(Invoice, invoice_id)
        if cached is not None:
            self.session.expire(cached, ["lines", "payments"])
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.student),
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
            )
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Invoice.branch_id, scope)
        stmt = self._family(stmt, actor)
        return self.session.scalar(stmt)

    def open_invoices(self, scope: BranchScope) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.payments))
            .where(
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(("issued", "partial", "overdue")),
            )
        )
        stmt = apply_branch_scope(stmt, Invoice.branch_id, scope)
        return list(self.session.scalars(stmt).all())

    def invoices_for_summary(self, scope: BranchScope) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.payments))
            .where(Invoice.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Invoice.branch_id, scope)
        return list(self.session.scalars(stmt).all())

    def payment_by_key(self, key: str) -> Payment | None:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.invoice), selectinload(Payment.student))
            .where(Payment.idempotency_key == key, Payment.deleted_at.is_(None))
        )
        if self.session.get_bind().dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def get_payment(self, payment_id: int, scope: BranchScope, actor: Actor) -> Payment | None:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.invoice), selectinload(Payment.student))
            .where(Payment.id == payment_id, Payment.deleted_at.is_(None))
        )
        stmt = apply_branch_scope(stmt, Payment.branch_id, scope)
        if limits_to_linked_children(actor) or limits_to_self(actor):
            stmt = self._family_payment(stmt, actor)
        return self.session.scalar(stmt)

    def completed_between(self, scope: BranchScope, start: date, end: date) -> list[Payment]:
        stmt = select(Payment).where(
            Payment.deleted_at.is_(None),
            Payment.status == "completed",
            Payment.paid_on >= start,
            Payment.paid_on <= end,
        )
        stmt = apply_branch_scope(stmt, Payment.branch_id, scope)
        return list(self.session.scalars(stmt).all())

    def _family(self, stmt, actor: Actor):
        clauses = []
        if limits_to_linked_children(actor):
            clauses.append(Invoice.student_id.in_(_linked_student_ids(actor.id)))
        if limits_to_self(actor):
            clauses.append(
                Invoice.student_id.in_(
                    select(Student.id).where(
                        Student.user_id == actor.id, Student.deleted_at.is_(None)
                    )
                )
            )
        if not clauses:
            return stmt
        if len(clauses) == 1:
            return stmt.where(clauses[0])
        return stmt.where(or_(*clauses))

    def _family_payment(self, stmt, actor: Actor):
        clauses = []
        if limits_to_linked_children(actor):
            clauses.append(Payment.student_id.in_(_linked_student_ids(actor.id)))
        if limits_to_self(actor):
            clauses.append(
                Payment.student_id.in_(
                    select(Student.id).where(
                        Student.user_id == actor.id, Student.deleted_at.is_(None)
                    )
                )
            )
        if not clauses:
            return stmt
        if len(clauses) == 1:
            return stmt.where(clauses[0])
        return stmt.where(or_(*clauses))


def lock_row(session, model, row_id: int):
    """Lock one row on MariaDB. SQLite rejects FOR UPDATE."""
    return lock_by_id(session, model, row_id)
