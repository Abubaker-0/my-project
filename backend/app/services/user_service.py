"""Account administration: create, update, deactivate, and restore."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import hash_password, validate_password_strength
from app.core.time import utcnow
from app.domain.actor import Actor
from app.domain.scope import scope_for
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.repositories.branch_repository import BranchRepository
from app.repositories.rbac_repository import RbacRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.user import RoleAssignmentIn, UserCreate, UserPublic, UserUpdate
from app.services.audit_service import AuditService
from app.services.presenters import to_user_public
from app.services.transactions import commit_or_conflict

_PHONE = re.compile(r"^[0-9+\-() ]{6,32}$")


class UserService:
    """User lifecycle. Every change is audited and committed here."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RbacRepository(session)
        self.branches = BranchRepository(session)
        self.tokens = TokenRepository(session)
        self.audit = AuditService(session)

    def list_users(
        self,
        actor: Actor,
        *,
        branch_id: int | None,
        q: str | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[UserPublic]:
        """Return one page of accounts visible to the actor."""
        scope = scope_for(actor, branch_id)
        rows, total = self.users.list_users(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[to_user_public(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_user(self, actor: Actor, user_id: int, *, branch_id: int | None) -> UserPublic:
        """Return one visible account."""
        user = self._visible(actor, user_id, branch_id)
        return to_user_public(user)

    def create_user(self, actor: Actor, payload: UserCreate) -> UserPublic:
        """Create an account and its grants in a single transaction."""
        email = str(payload.email).strip().lower()
        validate_password_strength(payload.password)
        phone = self._clean_phone(payload.phone)
        existing = self.users.get_by_email(email, include_deleted=True)
        if existing is not None:
            if existing.deleted_at is not None:
                raise AppException(
                    409,
                    "CONFLICT",
                    "This email belongs to a deactivated account. Restore that account instead.",
                )
            raise AppException(409, "CONFLICT", "A user with this email already exists")
        grants = self._validated_grants(actor, payload.assignments)
        user = User(
            email=email,
            full_name=payload.full_name.strip(),
            phone=phone,
            password_hash=hash_password(payload.password),
            status=payload.status,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.session.add(user)
        self.session.flush()
        self._replace_grants(actor, user, grants)
        self.audit.record(
            action="create",
            entity="user",
            entity_id=user.id,
            actor_id=actor.id,
            branch_id=_audit_branch(grants),
            new_values=_snapshot(user, grants),
        )
        commit_or_conflict(self.session)
        created = self.users.get(user.id)
        assert created is not None
        return to_user_public(created)

    def update_user(
        self, actor: Actor, user_id: int, payload: UserUpdate, *, branch_id: int | None
    ) -> UserPublic:
        """Update profile fields and, when supplied, replace role grants."""
        user = self._visible(actor, user_id, branch_id)
        self._assert_can_manage(actor, user)
        old_grants = _current_grants(user)
        old = _snapshot(user, old_grants)
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if "phone" in payload.model_fields_set:
            user.phone = self._clean_phone(payload.phone)
        next_status = payload.status if payload.status is not None else user.status
        next_grants = (
            self._validated_grants(actor, payload.assignments)
            if payload.assignments is not None
            else old_grants
        )
        self._assert_keeps_super_admin(user, next_grants=next_grants, next_status=next_status)
        if payload.status is not None:
            user.status = payload.status
            if payload.status == "active":
                user.failed_login_count = 0
                user.locked_until = None
            else:
                self.tokens.revoke_all_for_user(user.id, utcnow())
        if payload.assignments is not None:
            self._replace_grants(actor, user, next_grants)
        user.updated_by = actor.id
        self.audit.record(
            action="update",
            entity="user",
            entity_id=user.id,
            actor_id=actor.id,
            branch_id=_audit_branch(next_grants),
            old_values=old,
            new_values=_snapshot(user, next_grants),
        )
        commit_or_conflict(self.session)
        updated = self.users.get(user.id)
        assert updated is not None
        return to_user_public(updated)

    def delete_user(self, actor: Actor, user_id: int, *, branch_id: int | None) -> None:
        """Soft-delete an account and revoke its sessions."""
        user = self._visible(actor, user_id, branch_id)
        self._assert_can_manage(actor, user)
        if user.id == actor.id:
            raise AppException(409, "CONFLICT", "You cannot deactivate your own account")
        self._assert_keeps_super_admin(user, next_status="inactive")
        grants = _current_grants(user)
        old = _snapshot(user, grants)
        user.deleted_at = utcnow()
        user.status = "inactive"
        user.updated_by = actor.id
        self.tokens.revoke_all_for_user(user.id, utcnow())
        self.audit.record(
            action="delete",
            entity="user",
            entity_id=user.id,
            actor_id=actor.id,
            branch_id=_audit_branch(grants),
            old_values=old,
            new_values={"deleted": True},
        )
        commit_or_conflict(self.session)

    def restore_user(self, actor: Actor, user_id: int) -> UserPublic:
        """Clear a soft delete. Only a Super Admin can restore accounts."""
        if not actor.is_super_admin:
            raise AppException(403, "FORBIDDEN", "Only a Super Admin can restore accounts")
        user = self.users.get(user_id, include_deleted=True)
        if user is None:
            raise AppException(404, "NOT_FOUND", "User not found")
        if user.deleted_at is None:
            raise AppException(409, "CONFLICT", "This account is already active")
        user.deleted_at = None
        user.status = "active"
        user.failed_login_count = 0
        user.locked_until = None
        user.updated_by = actor.id
        grants = _current_grants(user)
        self.audit.record(
            action="update",
            entity="user",
            entity_id=user.id,
            actor_id=actor.id,
            branch_id=_audit_branch(grants),
            new_values={"restored": True},
        )
        commit_or_conflict(self.session)
        restored = self.users.get(user.id)
        assert restored is not None
        return to_user_public(restored)

    def _visible(self, actor: Actor, user_id: int, branch_id: int | None) -> User:
        user = self.users.get_visible(user_id, scope_for(actor, branch_id))
        if user is None:
            raise AppException(404, "NOT_FOUND", "User not found")
        return user

    def _assert_can_manage(self, actor: Actor, user: User) -> None:
        if actor.is_super_admin:
            return
        for link in user.role_links:
            if link.role.name == "super_admin" or link.branch_id is None:
                raise AppException(403, "FORBIDDEN", "You cannot change this account")

    def _assert_keeps_super_admin(
        self,
        user: User,
        *,
        next_grants: list[tuple[Role, int | None]] | None = None,
        next_status: str | None = None,
    ) -> None:
        is_super = any(link.role.name == "super_admin" for link in user.role_links)
        if not is_super or user.status != "active" or user.deleted_at is not None:
            return
        remains = True
        if next_grants is not None:
            remains = any(role.name == "super_admin" for role, _branch in next_grants)
        if next_status is not None and next_status != "active":
            remains = False
        if remains:
            return
        if self.users.count_other_active_super_admins(user.id) < 1:
            raise AppException(
                409,
                "CONFLICT",
                "The system needs at least one active Super Admin",
            )

    def _validated_grants(
        self, actor: Actor, assignments: list[RoleAssignmentIn]
    ) -> list[tuple[Role, int | None]]:
        if not assignments:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "At least one role is required",
                details=[{"field": "assignments", "message": "Choose a role"}],
            )
        grants: list[tuple[Role, int | None]] = []
        seen: set[tuple[int, int | None]] = set()
        for item in assignments:
            role = self.roles.get_role(item.role_id)
            if role is None:
                raise AppException(
                    422,
                    "VALIDATION_ERROR",
                    "Unknown role",
                    details=[{"field": "assignments", "message": "Unknown role"}],
                )
            if role.name == "super_admin" and not actor.is_super_admin:
                raise AppException(403, "FORBIDDEN", "You cannot assign the Super Admin role")
            if item.branch_id is None:
                if not actor.is_super_admin:
                    raise AppException(403, "FORBIDDEN", "You cannot grant access to every branch")
            else:
                branch = self.branches.get_visible(item.branch_id, scope_for(actor, item.branch_id))
                if branch is None or branch.status != "active":
                    raise AppException(
                        422,
                        "VALIDATION_ERROR",
                        "Unknown branch",
                        details=[{"field": "assignments", "message": "Unknown branch"}],
                    )
            key = (role.id, item.branch_id)
            if key in seen:
                continue
            seen.add(key)
            grants.append((role, item.branch_id))
        return grants

    def _replace_grants(
        self, actor: Actor, user: User, grants: list[tuple[Role, int | None]]
    ) -> None:
        user.role_links.clear()
        self.session.flush()
        for role, branch_id in grants:
            user.role_links.append(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    branch_id=branch_id,
                    created_by=actor.id,
                )
            )
        self.session.flush()

    @staticmethod
    def _clean_phone(phone: str | None) -> str | None:
        if phone is None:
            return None
        cleaned = phone.strip()
        if not cleaned:
            return None
        if _PHONE.fullmatch(cleaned) is None:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Enter a valid phone number",
                details=[{"field": "phone", "message": "Use digits, spaces, +, -, or parentheses"}],
            )
        return cleaned


def _current_grants(user: User) -> list[tuple[Role, int | None]]:
    return [(link.role, link.branch_id) for link in user.role_links if link.role.deleted_at is None]


def _snapshot(user: User, grants: list[tuple[Role, int | None]]) -> dict:
    return {
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "status": user.status,
        "roles": [{"role": role.name, "branch_id": branch_id} for role, branch_id in grants],
    }


def _audit_branch(grants: list[tuple[Role, int | None]]) -> int | None:
    branch_ids = {branch_id for _role, branch_id in grants if branch_id is not None}
    if len(branch_ids) == 1 and all(branch_id is not None for _role, branch_id in grants):
        return next(iter(branch_ids))
    return None
