"""Inquiry pipeline and conversion to admission."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.people import Inquiry
from app.schemas.common import Page
from app.schemas.records import (
    ConvertInquiry,
    FollowupCreate,
    InquiryCreate,
    InquiryDetail,
    InquiryPublic,
    InquiryUpdate,
    StudentDetail,
)
from app.services.inquiry_service import InquiryService

router = APIRouter(prefix="/inquiries", tags=["inquiries"])

_SORT = {
    "name": Inquiry.name,
    "status": Inquiry.status,
    "created_at": Inquiry.created_at,
    "follow_up_date": Inquiry.follow_up_date,
}


@router.get("", response_model=Page[InquiryPublic])
def list_inquiries(
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
    status_filter: str | None = Query(default=None, alias="status"),
) -> Page[InquiryPublic]:
    """List inquiries."""
    return InquiryService(db).list_inquiries(
        scope,
        q=page.q,
        status=status_filter,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "-created_at"),
    )


@router.post("", response_model=InquiryDetail, status_code=status.HTTP_201_CREATED)
def create_inquiry(
    payload: InquiryCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InquiryDetail:
    """Record a lead."""
    return InquiryService(db).create_inquiry(actor, scope, payload)


@router.get("/{inquiry_id}", response_model=InquiryDetail)
def get_inquiry(
    inquiry_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InquiryDetail:
    """Fetch one inquiry."""
    return InquiryService(db).get_inquiry(scope, inquiry_id)


@router.patch("/{inquiry_id}", response_model=InquiryDetail)
def update_inquiry(
    inquiry_id: int,
    payload: InquiryUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InquiryDetail:
    """Update a lead."""
    return InquiryService(db).update_inquiry(actor, scope, inquiry_id, payload)


@router.delete("/{inquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inquiry(
    inquiry_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a lead that was not converted."""
    InquiryService(db).delete_inquiry(actor, scope, inquiry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{inquiry_id}/followups", response_model=InquiryDetail, status_code=status.HTTP_201_CREATED
)
def add_followup(
    inquiry_id: int,
    payload: FollowupCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InquiryDetail:
    """Add a follow-up note."""
    return InquiryService(db).add_followup(actor, scope, inquiry_id, payload)


@router.post(
    "/{inquiry_id}/convert", response_model=StudentDetail, status_code=status.HTTP_201_CREATED
)
def convert_inquiry(
    inquiry_id: int,
    payload: ConvertInquiry,
    db: DbSession,
    actor: Actor = Depends(require_permission("inquiries:convert")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Turn a lead into a student."""
    return InquiryService(db).convert(actor, scope, inquiry_id, payload)
