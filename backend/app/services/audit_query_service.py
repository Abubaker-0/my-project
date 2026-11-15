"""Read side of the audit log. Writes go through AuditService."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.actor import Actor
from app.domain.scope import scope_for
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogPublic
from app.schemas.common import Page
from app.services.presenters import to_audit


class AuditQueryService:
    """Lists audit rows inside the caller's branch scope."""

    def __init__(self, session: Session) -> None:
        self.audits = AuditRepository(session)

    def list_logs(
        self,
        actor: Actor,
        *,
        branch_id: int | None,
        action: str | None,
        entity: str | None,
        q: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[AuditLogPublic]:
        """Return one page of audit records."""
        scope = scope_for(actor, branch_id)
        rows, total = self.audits.list_logs(
            scope,
            action=action,
            entity=entity,
            q=q,
            date_from=date_from,
            date_to=date_to,
            offset=(page - 1) * page_size,
            limit=page_size,
            order=order,
        )
        return Page(
            items=[to_audit(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
