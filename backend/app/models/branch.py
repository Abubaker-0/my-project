"""Campuses. Every later business table points at a branch."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_pk
from app.models.mixins import AuditUserMixin


class Branch(AuditUserMixin, Base):
    """A tuition centre location."""

    __tablename__ = "branches"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)

    role_links: Mapped[list[UserRole]] = relationship(back_populates="branch")


from app.models.rbac import UserRole  # noqa: E402
