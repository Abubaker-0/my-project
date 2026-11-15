"""Seats in a batch. An open seat is unique per student; withdrawn rows stay for history."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_fk, bigint_pk, pk_type
from app.models.mixins import AuditUserMixin


class Enrollment(AuditUserMixin, Base):
    """A student's place in a batch.

    `open_student_id` is the student id while the seat is active or waitlisted,
    and NULL after withdrawal or completion. The unique key therefore allows a
    history of closed seats and still rejects two open seats for the same
    student in one batch. MariaDB stores the generated value; it is not written
    by the application.
    """

    __tablename__ = "enrollments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'waitlisted', 'withdrawn', 'completed')",
            name="status",
        ),
        UniqueConstraint("batch_id", "open_student_id", name="uq_enrollments_open_student"),
        Index("ix_enrollments_branch_id_status", "branch_id", "status"),
        Index("ix_enrollments_batch_id_status", "batch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    student_id: Mapped[int] = bigint_fk("students.id")
    batch_id: Mapped[int] = bigint_fk("batches.id")
    enrolled_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    waitlist_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    open_student_id: Mapped[int | None] = mapped_column(
        pk_type(),
        Computed(
            "CASE WHEN status IN ('active', 'waitlisted') THEN student_id ELSE NULL END",
            persisted=True,
        ),
    )

    student: Mapped[Student] = relationship()
    batch: Mapped[Batch] = relationship()


from app.models.academics import Batch  # noqa: E402
from app.models.people import Student  # noqa: E402
