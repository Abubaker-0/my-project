"""Calendars, rooms, courses, batches, and the staff link used to assign teachers."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_fk, bigint_pk
from app.models.mixins import AuditUserMixin


class NumberSequence(AuditUserMixin, Base):
    """Allocates the next admission or employee number for one branch."""

    __tablename__ = "number_sequences"
    __table_args__ = (
        UniqueConstraint("branch_id", "doc_type", name="uq_number_sequences_branch_type"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AcademicYear(AuditUserMixin, Base):
    """A campus calendar. One year per branch is marked current."""

    __tablename__ = "academic_years"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="dates"),
        Index("ix_academic_years_branch_id_is_current", "branch_id", "is_current"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    terms: Mapped[list[Term]] = relationship(back_populates="academic_year")


class Term(AuditUserMixin, Base):
    """A term inside an academic year. Batches belong to a term."""

    __tablename__ = "terms"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="dates"),
        Index("ix_terms_branch_id_academic_year_id", "branch_id", "academic_year_id"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    academic_year_id: Mapped[int] = bigint_fk("academic_years.id")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    academic_year: Mapped[AcademicYear] = relationship(back_populates="terms")


class Room(AuditUserMixin, Base):
    """A classroom. Capacity is how many people the room can hold."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity >= 1", name="capacity"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        Index("ix_rooms_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Subject(AuditUserMixin, Base):
    """A subject taught at one campus, such as Mathematics."""

    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("branch_id", "code", name="uq_subjects_branch_code"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        Index("ix_subjects_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Course(AuditUserMixin, Base):
    """A subject offered at a level, such as Grade 8 Mathematics."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("duration_weeks >= 1", name="duration"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        Index("ix_courses_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    subject_id: Mapped[int] = bigint_fk("subjects.id")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    subject: Mapped[Subject] = relationship()


class Staff(AuditUserMixin, Base):
    """A staff profile. Phase 1 uses it to assign teachers to batches."""

    __tablename__ = "staff"
    __table_args__ = (
        UniqueConstraint("branch_id", "user_id", name="uq_staff_branch_user"),
        UniqueConstraint("branch_id", "employee_no", name="uq_staff_branch_employee_no"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        Index("ix_staff_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    user_id: Mapped[int] = bigint_fk("users.id")
    employee_no: Mapped[str] = mapped_column(String(32), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False, default="Teacher")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    user: Mapped[User] = relationship()


class Batch(AuditUserMixin, Base):
    """One offering of a course in a term, with a seat capacity."""

    __tablename__ = "batches"
    __table_args__ = (
        CheckConstraint("capacity >= 1", name="capacity"),
        CheckConstraint("end_date >= start_date", name="dates"),
        CheckConstraint("status IN ('planned', 'active', 'completed', 'cancelled')", name="status"),
        Index("ix_batches_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    course_id: Mapped[int] = bigint_fk("courses.id")
    term_id: Mapped[int] = bigint_fk("terms.id")
    room_id: Mapped[int | None] = bigint_fk("rooms.id", nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")

    course: Mapped[Course] = relationship()
    term: Mapped[Term] = relationship()
    room: Mapped[Room | None] = relationship()
    teachers: Mapped[list[BatchTeacher]] = relationship(back_populates="batch")


class BatchTeacher(Base):
    """Assigns a staff member to a batch as primary teacher or assistant."""

    __tablename__ = "batch_teachers"
    __table_args__ = (
        UniqueConstraint("batch_id", "staff_id", name="uq_batch_teachers_assignment"),
        CheckConstraint("role IN ('primary', 'assistant')", name="role"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    batch_id: Mapped[int] = bigint_fk("batches.id", ondelete="CASCADE")
    staff_id: Mapped[int] = bigint_fk("staff.id")
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    batch: Mapped[Batch] = relationship(back_populates="teachers")
    staff: Mapped[Staff] = relationship()


from app.models.user import User  # noqa: E402
