"""Roles, permissions, and the branch-scoped grants that connect them to users."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_fk, bigint_pk, pk_type
from app.models.mixins import AuditUserMixin

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        pk_type(),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        pk_type(),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_unicode_ci",
)


class Permission(Base):
    """A single `module:action` code."""

    __tablename__ = "permissions"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    id: Mapped[int] = bigint_pk()
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )


class Role(AuditUserMixin, Base):
    """A named bundle of permissions. Seeded roles are marked system."""

    __tablename__ = "roles"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    id: Mapped[int] = bigint_pk()
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    is_system: Mapped[bool] = mapped_column(nullable=False, default=False)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, back_populates="roles"
    )
    user_links: Mapped[list[UserRole]] = relationship(back_populates="role")


class UserRole(Base):
    """Assigns a role to a user.

    `branch_id` NULL means the grant covers every branch. `branch_key` makes
    that single global grant enforceable on MariaDB, which allows duplicate
    NULLs inside a unique index.
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "branch_key", name="uq_user_roles_assignment"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    user_id: Mapped[int] = bigint_fk("users.id", ondelete="CASCADE")
    role_id: Mapped[int] = bigint_fk("roles.id")
    branch_id: Mapped[int | None] = bigint_fk("branches.id", nullable=True)
    # MariaDB rejects NOT NULL after a STORED generated column. COALESCE makes
    # the value non-null in practice, which is what the unique key relies on.
    branch_key: Mapped[int | None] = mapped_column(
        BigInteger, Computed("COALESCE(branch_id, 0)", persisted=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    user: Mapped[User] = relationship(back_populates="role_links")
    role: Mapped[Role] = relationship(back_populates="user_links")
    branch: Mapped[Branch | None] = relationship(back_populates="role_links")


from app.models.branch import Branch  # noqa: E402
from app.models.user import User  # noqa: E402
