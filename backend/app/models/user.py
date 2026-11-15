"""Login accounts. Branch access lives on user_roles, not on the user row."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_pk
from app.models.mixins import AuditUserMixin


class User(AuditUserMixin, Base):
    """A person who can sign in."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'locked')", name="status"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    role_links: Mapped[list[UserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")


from app.models.rbac import UserRole  # noqa: E402
from app.models.token import RefreshToken  # noqa: E402
