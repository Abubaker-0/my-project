"""Students, guardians, documents, and the inquiry pipeline."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_fk, bigint_pk, pk_type
from app.models.mixins import AuditUserMixin


class Student(AuditUserMixin, Base):
    """An admitted learner. `admission_no` is allocated from the branch sequence."""

    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'graduated', 'dropped', 'suspended')",
            name="status",
        ),
        CheckConstraint("gender IN ('female', 'male', 'other', 'unspecified')", name="gender"),
        Index("ix_students_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    user_id: Mapped[int | None] = bigint_fk("users.id", nullable=True, ondelete="SET NULL")
    admission_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(32), nullable=False, default="unspecified")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)

    guardian_links: Mapped[list[StudentGuardian]] = relationship(back_populates="student")
    documents: Mapped[list[StudentDocument]] = relationship(back_populates="student")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Guardian(AuditUserMixin, Base):
    """An adult linked to one or more students. `user_id` is set for a parent login."""

    __tablename__ = "guardians"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    user_id: Mapped[int | None] = mapped_column(
        pk_type(), ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_name: Mapped[str] = mapped_column("relationship", String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    student_links: Mapped[list[StudentGuardian]] = relationship(back_populates="guardian")


class StudentGuardian(Base):
    """Links a guardian to a student and records what that guardian may do."""

    __tablename__ = "student_guardians"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    student_id: Mapped[int] = mapped_column(
        pk_type(), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    guardian_id: Mapped[int] = mapped_column(
        pk_type(), ForeignKey("guardians.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_pay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_view: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    student: Mapped[Student] = relationship(back_populates="guardian_links")
    guardian: Mapped[Guardian] = relationship(back_populates="student_links")


class StudentDocument(AuditUserMixin, Base):
    """A file stored for a student. The bytes live under the upload directory."""

    __tablename__ = "student_documents"
    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('birth_certificate', 'photo', 'report', 'id_copy', 'other')",
            name="doc_type",
        ),
        Index("ix_student_documents_branch_id_student_id", "branch_id", "student_id"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    student_id: Mapped[int] = bigint_fk("students.id", ondelete="CASCADE")
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    uploaded_by: Mapped[int] = bigint_fk("users.id")

    student: Mapped[Student] = relationship(back_populates="documents")


class Inquiry(AuditUserMixin, Base):
    """A lead. Conversion creates a student and stores that id here."""

    __tablename__ = "inquiries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'qualified', 'converted', 'lost')",
            name="status",
        ),
        CheckConstraint(
            "source IN ('walk_in', 'phone', 'website', 'referral', 'other')",
            name="source",
        ),
        Index("ix_inquiries_branch_id_status", "branch_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    course_interest_id: Mapped[int | None] = bigint_fk("courses.id", nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="walk_in")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    assigned_to: Mapped[int | None] = bigint_fk("users.id", nullable=True, ondelete="SET NULL")
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_student_id: Mapped[int | None] = bigint_fk(
        "students.id", nullable=True, ondelete="SET NULL"
    )

    course: Mapped[Course | None] = relationship()
    followups: Mapped[list[InquiryFollowup]] = relationship(back_populates="inquiry")


class InquiryFollowup(Base):
    """A note on an inquiry. Follow-ups are appended, not edited."""

    __tablename__ = "inquiry_followups"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    id: Mapped[int] = bigint_pk()
    branch_id: Mapped[int] = bigint_fk("branches.id")
    inquiry_id: Mapped[int] = bigint_fk("inquiries.id", ondelete="CASCADE")
    note: Mapped[str] = mapped_column(Text, nullable=False)
    next_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    inquiry: Mapped[Inquiry] = relationship(back_populates="followups")


from app.models.academics import Course  # noqa: E402
