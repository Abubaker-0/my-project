"""Writes the audit trail. The calling service commits."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.context import client_ip_ctx, request_id_ctx, user_agent_ctx
from app.models.audit import AuditLog


class AuditService:
    """Stage audit rows for create, update, delete, login, and permission changes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        action: str,
        entity: str,
        entity_id: int | str | None = None,
        actor_id: int | None = None,
        branch_id: int | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Append one audit row to the current transaction.

        IP, user agent, and request id fall back to the values set by the
        request-context middleware when the caller does not pass them.
        """
        request_id = request_id_ctx.get()
        agent = user_agent if user_agent is not None else user_agent_ctx.get()
        row = AuditLog(
            user_id=actor_id,
            branch_id=branch_id,
            action=action,
            entity=entity,
            entity_id=None if entity_id is None else str(entity_id),
            old_values=old_values,
            new_values=new_values,
            ip=ip if ip is not None else client_ip_ctx.get(),
            request_id=None if request_id in {"", "-"} else request_id,
            user_agent=None if not agent else agent[:500],
        )
        self.session.add(row)
        return row
