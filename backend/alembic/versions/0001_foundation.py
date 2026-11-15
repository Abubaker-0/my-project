"""Foundation tables: identity, RBAC, branches, sessions, and audit.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PK = mysql.BIGINT(unsigned=True)
TABLE = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}


def _pk(name: str = "id") -> sa.Column:
    return sa.Column(name, PK, primary_key=True, autoincrement=True)


def _fk(name: str, target: str, *, nullable: bool = False, ondelete: str = "RESTRICT") -> sa.Column:
    return sa.Column(
        name, PK, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable, index=True
    )


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "permissions",
        _pk(),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        **TABLE,
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])

    op.create_table(
        "roles",
        _pk(),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.UniqueConstraint("name", name="uq_roles_name"),
        **TABLE,
    )
    op.create_index("ix_roles_deleted_at", "roles", ["deleted_at"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", PK, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "permission_id",
            PK,
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        **TABLE,
    )

    op.create_table(
        "branches",
        _pk(),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_branches_status"),
        sa.UniqueConstraint("code", name="uq_branches_code"),
        **TABLE,
    )
    op.create_index("ix_branches_status", "branches", ["status"])
    op.create_index("ix_branches_deleted_at", "branches", ["deleted_at"])

    op.create_table(
        "users",
        _pk(),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("mfa_secret", sa.String(length=255), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint("status IN ('active', 'inactive', 'locked')", name="ck_users_status"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        **TABLE,
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    op.create_table(
        "user_roles",
        _pk(),
        _fk("user_id", "users.id", ondelete="CASCADE"),
        _fk("role_id", "roles.id"),
        _fk("branch_id", "branches.id", nullable=True),
        sa.Column(
            "branch_key",
            sa.BigInteger(),
            sa.Computed("COALESCE(branch_id, 0)", persisted=True),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("user_id", "role_id", "branch_key", name="uq_user_roles_assignment"),
        **TABLE,
    )

    op.create_table(
        "refresh_tokens",
        _pk(),
        _fk("user_id", "users.id", ondelete="CASCADE"),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by_id", PK, nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        **TABLE,
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_foreign_key(
        "fk_refresh_tokens_replaced_by_id_refresh_tokens",
        "refresh_tokens",
        "refresh_tokens",
        ["replaced_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "password_resets",
        _pk(),
        _fk("user_id", "users.id", ondelete="CASCADE"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_password_resets_token_hash"),
        **TABLE,
    )

    op.create_table(
        "audit_logs",
        _pk(),
        _fk("user_id", "users.id", nullable=True, ondelete="SET NULL"),
        _fk("branch_id", "branches.id", nullable=True, ondelete="SET NULL"),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        **TABLE,
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_branch_created", "audit_logs", ["branch_id", "created_at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("password_resets")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("branches")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
