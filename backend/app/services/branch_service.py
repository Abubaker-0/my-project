"""Branch list for the shell, plus create, update, and archive."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.domain.scope import scope_for
from app.models.academics import NumberSequence
from app.models.branch import Branch
from app.repositories.branch_repository import BranchRepository
from app.schemas.branch import BranchPublic
from app.schemas.common import Page
from app.schemas.records import BranchCreate, BranchUpdate
from app.services.audit_service import AuditService
from app.services.guards import (
    clean_phone,
    ensure_branch,
    not_found,
    snapshot,
    soft_delete,
    stamp_new,
    stamp_update,
)
from app.services.presenters import to_branch
from app.services.transactions import commit_or_conflict


class BranchService:
    """Lists campuses the caller is allowed to see."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.branches = BranchRepository(session)
        self.audit = AuditService(session)

    def list_branches(
        self,
        actor: Actor,
        *,
        branch_id: int | None,
        q: str | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[BranchPublic]:
        """Return one page of branches inside the caller's scope."""
        scope = scope_for(actor, branch_id)
        rows, total = self.branches.list_branches(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[to_branch(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_branch(
        self, actor: Actor, branch_id: int, *, selected_branch_id: int | None
    ) -> BranchPublic:
        """Return one branch, or 404 when it is outside the caller's scope."""
        scope = scope_for(actor, selected_branch_id)
        branch = self.branches.get_visible(branch_id, scope)
        if branch is None:
            raise AppException(404, "NOT_FOUND", "Branch not found")
        return to_branch(branch)

    def create_branch(
        self, actor: Actor, scope: BranchScope, payload: BranchCreate
    ) -> BranchPublic:
        """Create a campus and its admission-number sequence."""
        code = payload.code.strip().upper()
        if self.branches.get_by_code(code) is not None:
            raise AppException(409, "CONFLICT", "A branch with this code already exists")
        branch = Branch(
            code=code,
            name=payload.name.strip(),
            address=_clean(payload.address),
            phone=clean_phone(payload.phone),
            email=str(payload.email).strip().lower() if payload.email else None,
            status="active",
        )
        stamp_new(branch, actor.id)
        self.session.add(branch)
        self.session.flush()
        self.session.add(
            NumberSequence(
                branch_id=branch.id,
                doc_type="admission",
                prefix=f"{code}-{date.today().year}-",
                next_number=1,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        self.audit.record(
            action="create",
            entity="branch",
            entity_id=branch.id,
            actor_id=actor.id,
            branch_id=branch.id,
            new_values=snapshot(branch, ("code", "name", "status")),
        )
        commit_or_conflict(self.session)
        return to_branch(branch)

    def update_branch(
        self, actor: Actor, scope: BranchScope, branch_id: int, payload: BranchUpdate
    ) -> BranchPublic:
        """Update a campus the caller can see."""
        ensure_branch(scope, branch_id)
        branch = self.branches.get_visible(branch_id, scope)
        if branch is None:
            raise not_found("Branch")
        old = snapshot(branch, ("name", "status", "phone", "email"))
        if payload.name is not None:
            branch.name = payload.name.strip()
        if "address" in payload.model_fields_set:
            branch.address = _clean(payload.address)
        if "phone" in payload.model_fields_set:
            branch.phone = clean_phone(payload.phone)
        if "email" in payload.model_fields_set:
            branch.email = str(payload.email).strip().lower() if payload.email else None
        if payload.status is not None:
            branch.status = payload.status
        stamp_update(branch, actor.id)
        self.audit.record(
            action="update",
            entity="branch",
            entity_id=branch.id,
            actor_id=actor.id,
            branch_id=branch.id,
            old_values=old,
            new_values=snapshot(branch, ("name", "status", "phone", "email")),
        )
        commit_or_conflict(self.session)
        return to_branch(branch)

    def delete_branch(self, actor: Actor, scope: BranchScope, branch_id: int) -> None:
        """Archive a campus that has no students."""
        ensure_branch(scope, branch_id)
        branch = self.branches.get_visible(branch_id, scope)
        if branch is None:
            raise not_found("Branch")
        if self.branches.student_count(branch.id):
            raise AppException(
                409, "CONFLICT", "Move or archive the students before archiving this campus"
            )
        soft_delete(branch, actor.id)
        self.audit.record(
            action="delete",
            entity="branch",
            entity_id=branch.id,
            actor_id=actor.id,
            branch_id=branch.id,
            old_values={"code": branch.code, "name": branch.name},
        )
        commit_or_conflict(self.session)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
