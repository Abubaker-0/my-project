"""Weekly timetable, attendance, fee plans, invoices, and payments."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import MONEY, bigint_fk, bigint_pk
from app.models.academics import Batch, Room, Staff
from app.models.mixins import AuditUserMixin
from app.models.people import Student


class ClassSession(AuditUserMixin, Base):
    """One weekly slot for a batch. Cancelled slots stay on record and free the room."""

    __tablename__ = "class_sessions"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday"),
        CheckConstraint("end_time > start_time", name="times"),
        CheckConstraint("ends_on >= starts_on", name="dates"),
        CheckConstraint("status IN ('scheduled', 'cancelled')", name="status"),
        Index("ix_class_sessions_branch_id_status", "branch_id", "status"),
        Index("ix_class_sessions_weekday", "weekday"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    batch_id: Mapped[int] = bigint_fk("batches.id")
    room_id: Mapped[int | None] = bigint_fk("rooms.id", nullable=True)
    staff_id: Mapped[int | None] = bigint_fk("staff.id", nullable=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")

    batch: Mapped[Batch] = relationship()
    room: Mapped[Room | None] = relationship()
    staff: Mapped[Staff | None] = relationship()


class AttendanceSheet(AuditUserMixin, Base):
    """The register for one batch on one date."""

    __tablename__ = "attendance_sheets"
    __table_args__ = (
        UniqueConstraint("batch_id", "attended_on", name="uq_attendance_sheets_batch_date"),
        Index("ix_attendance_sheets_branch_id_attended_on", "branch_id", "attended_on"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    batch_id: Mapped[int] = bigint_fk("batches.id")
    attended_on: Mapped[date] = mapped_column(Date, nullable=False)

    batch: Mapped[Batch] = relationship()
    marks: Mapped[list[AttendanceMark]] = relationship(back_populates="sheet")


class AttendanceMark(AuditUserMixin, Base):
    """One student's mark on a register. Unmarked students are simply absent from this table."""

    __tablename__ = "attendance_marks"
    __table_args__ = (
        UniqueConstraint("sheet_id", "student_id", name="uq_attendance_marks_sheet_student"),
        CheckConstraint("status IN ('present', 'absent', 'late', 'excused')", name="status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    sheet_id: Mapped[int] = bigint_fk("attendance_sheets.id")
    student_id: Mapped[int] = bigint_fk("students.id")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sheet: Mapped[AttendanceSheet] = relationship(back_populates="marks")
    student: Mapped[Student] = relationship()


class FeePlan(AuditUserMixin, Base):
    """A reusable charge, such as monthly tuition for a course."""

    __tablename__ = "fee_plans"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount"),
        CheckConstraint("billing_period IN ('once', 'monthly', 'term')", name="billing_period"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        Index("ix_fee_plans_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    course_id: Mapped[int | None] = bigint_fk("courses.id", nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    billing_period: Mapped[str] = mapped_column(String(32), nullable=False, default="monthly")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Invoice(AuditUserMixin, Base):
    """A bill. Rows are cancelled with a reason and are never removed."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_no", name="uq_invoices_invoice_no"),
        CheckConstraint("total >= 0", name="total"),
        CheckConstraint("due_date >= issue_date", name="dates"),
        CheckConstraint(
            "status IN ('issued', 'partial', 'paid', 'overdue', 'cancelled')",
            name="status",
        ),
        Index("ix_invoices_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    student_id: Mapped[int] = bigint_fk("students.id")
    fee_plan_id: Mapped[int | None] = bigint_fk("fee_plans.id", nullable=True)
    invoice_no: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    total: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="issued")
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    student: Mapped[Student] = relationship()
    lines: Mapped[list[InvoiceLine]] = relationship(back_populates="invoice")
    payments: Mapped[list[Payment]] = relationship(back_populates="invoice")

    @property
    def amount_paid(self) -> Decimal:
        paid = Decimal("0.00")
        for payment in self.payments:
            if payment.deleted_at is None and payment.status == "completed":
                paid += payment.amount
        return paid

    @property
    def balance(self) -> Decimal:
        return self.total - self.amount_paid


class InvoiceLine(AuditUserMixin, Base):
    """One charge on an invoice."""

    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    invoice_id: Mapped[int] = bigint_fk("invoices.id")
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class Payment(AuditUserMixin, Base):
    """Money received against an invoice. A void keeps the row and the reason."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("receipt_no", name="uq_payments_receipt_no"),
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        CheckConstraint("amount > 0", name="amount"),
        CheckConstraint("method IN ('cash', 'card', 'bank', 'other')", name="method"),
        CheckConstraint("status IN ('completed', 'void')", name="status"),
        Index("ix_payments_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    invoice_id: Mapped[int] = bigint_fk("invoices.id")
    student_id: Mapped[int] = bigint_fk("students.id")
    receipt_no: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(200), nullable=False)
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
    student: Mapped[Student] = relationship()
