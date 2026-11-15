"""Academic years, terms, and rooms."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.academics import AcademicYear, Room
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
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["organization"])

_YEAR_SORT = {
    "name": AcademicYear.name,
    "start_date": AcademicYear.start_date,
    "created_at": AcademicYear.created_at,
}
_ROOM_SORT = {"name": Room.name, "capacity": Room.capacity, "created_at": Room.created_at}


@router.get("/academic-years", response_model=Page[AcademicYearPublic])
def list_years(
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[AcademicYearPublic]:
    """List academic years in the selected campus scope."""
    return OrganizationService(db).list_years(
        scope,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _YEAR_SORT, "start_date"),
    )


@router.post(
    "/academic-years", response_model=AcademicYearDetail, status_code=status.HTTP_201_CREATED
)
def create_year(
    payload: AcademicYearCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> AcademicYearDetail:
    """Create an academic year."""
    return OrganizationService(db).create_year(actor, scope, payload)


@router.get("/academic-years/{year_id}", response_model=AcademicYearDetail)
def get_year(
    year_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> AcademicYearDetail:
    """Fetch one year and its terms."""
    return OrganizationService(db).get_year(scope, year_id)


@router.patch("/academic-years/{year_id}", response_model=AcademicYearDetail)
def update_year(
    year_id: int,
    payload: AcademicYearUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> AcademicYearDetail:
    """Update an academic year."""
    return OrganizationService(db).update_year(actor, scope, year_id, payload)


@router.delete("/academic-years/{year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_year(
    year_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive an academic year that has no terms."""
    OrganizationService(db).delete_year(actor, scope, year_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/academic-years/{year_id}/terms",
    response_model=AcademicYearDetail,
    status_code=status.HTTP_201_CREATED,
)
def add_term(
    year_id: int,
    payload: TermCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> AcademicYearDetail:
    """Add a term inside a year."""
    return OrganizationService(db).add_term(actor, scope, year_id, payload)


@router.patch("/terms/{term_id}", response_model=TermPublic)
def update_term(
    term_id: int,
    payload: TermUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> TermPublic:
    """Update a term."""
    return OrganizationService(db).update_term(actor, scope, term_id, payload)


@router.delete("/terms/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_term(
    term_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("academic_years:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a term that has no batches."""
    OrganizationService(db).delete_term(actor, scope, term_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/rooms", response_model=Page[RoomPublic])
def list_rooms(
    db: DbSession,
    actor: Actor = Depends(require_permission("rooms:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[RoomPublic]:
    """List classrooms."""
    return OrganizationService(db).list_rooms(
        scope,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _ROOM_SORT, "name"),
    )


@router.post("/rooms", response_model=RoomPublic, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("rooms:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> RoomPublic:
    """Create a classroom."""
    return OrganizationService(db).create_room(actor, scope, payload)


@router.get("/rooms/{room_id}", response_model=RoomPublic)
def get_room(
    room_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("rooms:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> RoomPublic:
    """Fetch one classroom."""
    return OrganizationService(db).get_room(scope, room_id)


@router.patch("/rooms/{room_id}", response_model=RoomPublic)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("rooms:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> RoomPublic:
    """Update a classroom."""
    return OrganizationService(db).update_room(actor, scope, room_id, payload)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("rooms:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a classroom."""
    OrganizationService(db).delete_room(actor, scope, room_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
