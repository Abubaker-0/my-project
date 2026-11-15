"""Allocate admission and employee numbers inside the caller's transaction."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academics import NumberSequence


class NumberingService:
    """Hands out the next formatted number for a branch and document type."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def allocate(self, branch_id: int, doc_type: str, prefix: str, actor_id: int | None) -> str:
        """Return the next number, such as `MAIN-2026-0001`, and advance the sequence.

        The row is locked on MariaDB so two admissions cannot take the same value.
        SQLite tests run one transaction at a time, so the lock is unnecessary there.
        """
        stmt = select(NumberSequence).where(
            NumberSequence.branch_id == branch_id,
            NumberSequence.doc_type == doc_type,
            NumberSequence.deleted_at.is_(None),
        )
        if self.session.get_bind().dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        row = self.session.scalar(stmt)
        if row is None:
            row = NumberSequence(
                branch_id=branch_id,
                doc_type=doc_type,
                prefix=prefix,
                next_number=1,
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.session.add(row)
            self.session.flush()
        current = row.next_number
        row.next_number = current + 1
        if actor_id is not None:
            row.updated_by = actor_id
        return f"{row.prefix}{current:04d}"
