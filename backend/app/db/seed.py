"""Idempotent seed for roles, permissions, the main branch, a super admin, and sample records."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.security import hash_password, validate_password_strength
from app.db.catalog import PERMISSIONS, ROLE_DEFINITIONS
from app.db.operations_sample import seed_operations
from app.db.sample_data import seed_samples
from app.db.session import get_session_factory
from app.models.branch import Branch
from app.models.rbac import Permission, Role, UserRole
from app.models.user import User

logger = logging.getLogger(__name__)


def seed(session: Session) -> None:
    """Insert foundation data. Safe to run more than once.

    The super admin password is set only when that account is created. Later
    runs do not overwrite it. Super Admin permissions are refreshed so new
    codes are granted. Other system roles keep permission edits made in the UI.
    """
    settings = get_settings()
    validate_password_strength(settings.seed_admin_password)
    permissions = _sync_permissions(session)
    roles = _sync_roles(session, permissions)
    branch = _sync_branch(session)
    admin = _sync_admin(session, roles["super_admin"])
    if not get_settings().is_production:
        seed_samples(session, branch, admin)
        seed_operations(session, branch, admin)
    session.commit()
    logger.info("Seed complete")


def _sync_permissions(session: Session) -> dict[str, Permission]:
    by_code: dict[str, Permission] = {}
    for code, description, module in PERMISSIONS:
        row = session.scalar(select(Permission).where(Permission.code == code))
        if row is None:
            row = Permission(code=code, description=description, module=module)
            session.add(row)
            session.flush()
            logger.info("Created permission %s", code)
        else:
            row.description = description
            row.module = module
        by_code[code] = row
    return by_code


def _sync_roles(session: Session, permissions: dict[str, Permission]) -> dict[str, Role]:
    by_name: dict[str, Role] = {}
    for name, (label, description, codes) in ROLE_DEFINITIONS.items():
        role = session.scalar(select(Role).where(Role.name == name))
        created = role is None
        if role is None:
            role = Role(name=name, label=label, description=description, is_system=True)
            session.add(role)
            session.flush()
            logger.info("Created role %s", name)
        role.label = label
        role.description = description
        role.is_system = True
        role.deleted_at = None
        if created or name == "super_admin":
            role.permissions = [permissions[code] for code in sorted(codes)]
        by_name[name] = role
    session.flush()
    return by_name


def _sync_branch(session: Session) -> Branch:
    branch = session.scalar(select(Branch).where(Branch.code == "MAIN"))
    if branch is None:
        branch = Branch(
            code="MAIN",
            name="Main Campus",
            address="1 Campus Road",
            phone="000-000-0000",
            email="main@tuition.example",
            status="active",
        )
        session.add(branch)
        session.flush()
        logger.info("Created branch MAIN")
    return branch


def _sync_admin(session: Session, super_admin: Role) -> User:
    settings = get_settings()
    email = settings.seed_admin_email.strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name=settings.seed_admin_name.strip(),
            password_hash=hash_password(settings.seed_admin_password),
            status="active",
        )
        session.add(user)
        session.flush()
        logger.info("Created super admin %s", email)
    elif user.deleted_at is not None:
        user.deleted_at = None
        user.status = "active"
    link = session.scalar(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == super_admin.id,
            UserRole.branch_id.is_(None),
        )
    )
    if link is None:
        session.add(
            UserRole(user_id=user.id, role_id=super_admin.id, branch_id=None, created_by=user.id)
        )
        session.flush()
    return user


def main() -> None:
    """CLI entry point: `python -m app.db.seed`."""
    setup_logging()
    session = get_session_factory()()
    try:
        seed(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    settings = get_settings()
    print(f"Seed complete. Super admin: {settings.seed_admin_email}")


if __name__ == "__main__":
    main()
