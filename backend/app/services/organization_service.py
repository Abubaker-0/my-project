"""Academic years, terms, and rooms."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.models.academics import AcademicYear, Batch, Room, Term
from app.repositories.records import CalendarRepository, RoomRepository
from app.schemas.common import Page
from app.schemas.records import (
    AcademicYearCreate,
    AcademicYearDetail,
    AcademicYearPublic,
    AcademicYearUpdate,
    RoomCreate,
    RoomPublic,
    RoomUpdate,
    TermCreate,
    TermPublic,
    TermUpdate,
)
from app.services.audit_service import AuditService
from app.services.guards import (
    ensure_branch,
    not_found,
    require_order,
    snapshot,
    soft_delete,
    stamp_new,
    stamp_update,
)
from app.services.transactions import commit_or_conflict


class OrganizationService:
    """Campus calendar and classrooms. One year per campus is current."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.calendar = CalendarRepository(session)
        self.rooms = RoomRepository(session)
        self.audit = AuditService(session)

    def list_years(self, scope, *, q, page, page_size, order) -> Page[AcademicYearPublic]:
        """Return one page of academic years."""
        rows, total = self.calendar.list_years(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(items=[_year(row) for row in rows], total=total, page=page, page_size=page_size)

    def get_year(self, scope, year_id: int) -> AcademicYearDetail:
        """Return one year and the terms that have not been archived."""
        row = self.calendar.get_year(year_id, scope)
        if row is None:
            raise not_found("Academic year")
        return _year_detail(row)

    def create_year(
        self, actor: Actor, scope: BranchScope, payload: AcademicYearCreate
    ) -> AcademicYearDetail:
        """Add a year. Marking it current clears the previous current year."""
        ensure_branch(scope, payload.branch_id)
        require_order(payload.start_date, payload.end_date, "end_date")
        if payload.is_current:
            self.calendar.clear_current(payload.branch_id, None)
        row = AcademicYear(
            branch_id=payload.branch_id,
            name=payload.name.strip(),
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_current=payload.is_current,
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self._audit(actor, "create", "academic_year", row)
        commit_or_conflict(self.session)
        return self.get_year(scope, row.id)

    def update_year(
        self, actor, scope, year_id: int, payload: AcademicYearUpdate
    ) -> AcademicYearDetail:
        """Update a year and keep a single current year for the campus."""
        row = self.calendar.get_year(year_id, scope)
        if row is None:
            raise not_found("Academic year")
        start = payload.start_date or row.start_date
        end = payload.end_date or row.end_date
        require_order(start, end, "end_date")
        for term in row.terms:
            if term.deleted_at is None and (term.start_date < start or term.end_date > end):
                raise AppException(
                    422,
                    "VALIDATION_ERROR",
                    "The year must still cover its terms",
                    details=[
                        {
                            "field": "start_date",
                            "message": f"{term.name} would fall outside the year",
                        }
                    ],
                )
        if payload.name is not None:
            row.name = payload.name.strip()
        row.start_date = start
        row.end_date = end
        if payload.is_current:
            self.calendar.clear_current(row.branch_id, row.id)
            row.is_current = True
        elif payload.is_current is False:
            row.is_current = False
        stamp_update(row, actor.id)
        self._audit(actor, "update", "academic_year", row)
        commit_or_conflict(self.session)
        return self.get_year(scope, row.id)

    def delete_year(self, actor, scope, year_id: int) -> None:
        """Archive a year that has no terms."""
        row = self.calendar.get_year(year_id, scope)
        if row is None:
            raise not_found("Academic year")
        if any(term.deleted_at is None for term in row.terms):
            raise AppException(409, "CONFLICT", "Archive the terms in this year first")
        soft_delete(row, actor.id)
        self._audit(actor, "delete", "academic_year", row)
        commit_or_conflict(self.session)

    def add_term(self, actor, scope, year_id: int, payload: TermCreate) -> AcademicYearDetail:
        """Add a term whose dates sit inside the year."""
        year = self.calendar.get_year(year_id, scope)
        if year is None:
            raise not_found("Academic year")
        self._term_dates(year, payload.start_date, payload.end_date)
        term = Term(
            branch_id=year.branch_id,
            academic_year_id=year.id,
            name=payload.name.strip(),
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        stamp_new(term, actor.id)
        self.session.add(term)
        self.session.flush()
        self.audit.record(
            action="create",
            entity="term",
            entity_id=term.id,
            actor_id=actor.id,
            branch_id=year.branch_id,
            new_values=snapshot(term, ("name", "start_date", "end_date")),
        )
        commit_or_conflict(self.session)
        return self.get_year(scope, year.id)

    def update_term(self, actor, scope, term_id: int, payload: TermUpdate) -> TermPublic:
        """Update a term without letting it leave its year."""
        term = self.calendar.get_term(term_id, scope)
        if term is None:
            raise not_found("Term")
        year = self.calendar.get_year(term.academic_year_id, scope)
        if year is None:
            raise not_found("Academic year")
        start = payload.start_date or term.start_date
        end = payload.end_date or term.end_date
        self._term_dates(year, start, end)
        if payload.name is not None:
            term.name = payload.name.strip()
        term.start_date = start
        term.end_date = end
        stamp_update(term, actor.id)
        self.audit.record(
            action="update",
            entity="term",
            entity_id=term.id,
            actor_id=actor.id,
            branch_id=term.branch_id,
            new_values=snapshot(term, ("name", "start_date", "end_date")),
        )
        commit_or_conflict(self.session)
        return _term(term)

    def delete_term(self, actor, scope, term_id: int) -> None:
        """Archive a term. Batches that still point at it must be archived first."""
        term = self.calendar.get_term(term_id, scope)
        if term is None:
            raise not_found("Term")
        used = self.session.scalar(
            select(Batch.id).where(Batch.term_id == term.id, Batch.deleted_at.is_(None))
        )
        if used is not None:
            raise AppException(409, "CONFLICT", "Archive the batches in this term first")
        soft_delete(term, actor.id)
        self.audit.record(
            action="delete",
            entity="term",
            entity_id=term.id,
            actor_id=actor.id,
            branch_id=term.branch_id,
            old_values={"name": term.name},
        )
        commit_or_conflict(self.session)

    def list_rooms(self, scope, *, q, page, page_size, order) -> Page[RoomPublic]:
        """Return one page of rooms."""
        rows, total = self.rooms.list_rooms(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(items=[_room(row) for row in rows], total=total, page=page, page_size=page_size)

    def get_room(self, scope, room_id: int) -> RoomPublic:
        """Return one room."""
        row = self.rooms.get_room(room_id, scope)
        if row is None:
            raise not_found("Room")
        return _room(row)

    def create_room(self, actor, scope, payload: RoomCreate) -> RoomPublic:
        """Add a classroom."""
        ensure_branch(scope, payload.branch_id)
        if self.rooms.name_taken(payload.branch_id, payload.name.strip(), None):
            raise AppException(
                409, "CONFLICT", "A room with that name already exists at this campus"
            )
        row = Room(
            branch_id=payload.branch_id,
            name=payload.name.strip(),
            capacity=payload.capacity,
            status=payload.status,
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self._audit_room(actor, "create", row)
        commit_or_conflict(self.session)
        return _room(row)

    def update_room(self, actor, scope, room_id: int, payload: RoomUpdate) -> RoomPublic:
        """Update a classroom."""
        row = self.rooms.get_room(room_id, scope)
        if row is None:
            raise not_found("Room")
        if payload.name is not None and self.rooms.name_taken(
            row.branch_id, payload.name.strip(), row.id
        ):
            raise AppException(
                409, "CONFLICT", "A room with that name already exists at this campus"
            )
        if payload.name is not None:
            row.name = payload.name.strip()
        if payload.capacity is not None:
            row.capacity = payload.capacity
        if payload.status is not None:
            row.status = payload.status
        stamp_update(row, actor.id)
        self._audit_room(actor, "update", row)
        commit_or_conflict(self.session)
        return _room(row)

    def delete_room(self, actor, scope, room_id: int) -> None:
        """Archive a room."""
        row = self.rooms.get_room(room_id, scope)
        if row is None:
            raise not_found("Room")
        soft_delete(row, actor.id)
        self._audit_room(actor, "delete", row)
        commit_or_conflict(self.session)

    def _term_dates(self, year: AcademicYear, start, end) -> None:
        require_order(start, end, "end_date")
        if start < year.start_date or end > year.end_date:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Term dates must fall inside the academic year",
                details=[{"field": "start_date", "message": "Keep the term inside the year"}],
            )

    def _audit(self, actor, action: str, entity: str, row: AcademicYear) -> None:
        self.audit.record(
            action=action,
            entity=entity,
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            new_values=snapshot(row, ("name", "start_date", "end_date", "is_current")),
        )

    def _audit_room(self, actor, action: str, row: Room) -> None:
        self.audit.record(
            action=action,
            entity="room",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            new_values=snapshot(row, ("name", "capacity", "status")),
        )


def _year(row: AcademicYear) -> AcademicYearPublic:
    return AcademicYearPublic(
        id=row.id,
        branch_id=row.branch_id,
        name=row.name,
        start_date=row.start_date,
        end_date=row.end_date,
        is_current=row.is_current,
        created_at=row.created_at,
    )


def _year_detail(row: AcademicYear) -> AcademicYearDetail:
    terms = [_term(term) for term in row.terms if term.deleted_at is None]
    terms.sort(key=lambda item: item.start_date)
    base = _year(row).model_dump()
    return AcademicYearDetail(**base, terms=terms)


def _term(row: Term) -> TermPublic:
    return TermPublic(
        id=row.id,
        branch_id=row.branch_id,
        academic_year_id=row.academic_year_id,
        name=row.name,
        start_date=row.start_date,
        end_date=row.end_date,
    )


def _room(row: Room) -> RoomPublic:
    return RoomPublic(
        id=row.id,
        branch_id=row.branch_id,
        name=row.name,
        capacity=row.capacity,
        status=row.status,
        created_at=row.created_at,
    )
