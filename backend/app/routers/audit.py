"""Audit log read API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogPublic
from app.schemas.common import Page
from app.services.audit_query_service import AuditQueryService

router = APIRouter(prefix="/audit-logs", tags=["audit"])

_SORT = {"created_at": AuditLog.created_at, "action": AuditLog.action, "entity": AuditLog.entity}


@router.get("", response_model=Page[AuditLogPublic])
def list_audit_logs(
    db: DbSession,
    actor: Actor = Depends(require_permission("audit:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
    action: str | None = Query(default=None, max_length=64),
    entity: str | None = Query(default=None, max_length=64),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Page[AuditLogPublic]:
    """List audit records. Branch staff do not see events that have no branch."""
    selected = (
        scope.branch_ids[0] if not scope.unrestricted and len(scope.branch_ids) == 1 else None
    )
    return AuditQueryService(db).list_logs(
        actor,
        branch_id=None if scope.unrestricted else selected,
        action=action,
        entity=entity,
        q=page.q,
        date_from=date_from,
        date_to=date_to,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "-created_at"),
    )
