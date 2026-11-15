"""Students, guardians, and documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.people import Student
from app.schemas.common import Page
from app.schemas.records import (
    DocumentPublic,
    GuardianIn,
    StudentCreate,
    StudentDetail,
    StudentPublic,
    StudentTransfer,
    StudentUpdate,
)
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])

_SORT = {
    "admission_no": Student.admission_no,
    "first_name": Student.first_name,
    "last_name": Student.last_name,
    "status": Student.status,
    "admission_date": Student.admission_date,
    "created_at": Student.created_at,
}


@router.get("", response_model=Page[StudentPublic])
def list_students(
    db: DbSession,
    actor: Actor = Depends(require_permission("students:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
    status_filter: str | None = Query(default=None, alias="status"),
) -> Page[StudentPublic]:
    """List students the caller is allowed to see."""
    return StudentService(db).list_students(
        actor,
        scope,
        q=page.q,
        status=status_filter,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SORT, "admission_no"),
    )


@router.post("", response_model=StudentDetail, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("students:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Admit a student."""
    return StudentService(db).create_student(actor, scope, payload)


@router.get("/{student_id}", response_model=StudentDetail)
def get_student(
    student_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("students:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Fetch one student."""
    return StudentService(db).get_student(actor, scope, student_id)


@router.patch("/{student_id}", response_model=StudentDetail)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("students:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Update a student."""
    return StudentService(db).update_student(actor, scope, student_id, payload)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("students:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a student and free their open seats."""
    StudentService(db).delete_student(actor, scope, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{student_id}/transfer", response_model=StudentDetail)
def transfer_student(
    student_id: int,
    payload: StudentTransfer,
    db: DbSession,
    actor: Actor = Depends(require_permission("students:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Move a student to another campus."""
    return StudentService(db).transfer_branch(actor, scope, student_id, payload.branch_id)


@router.post(
    "/{student_id}/guardians", response_model=StudentDetail, status_code=status.HTTP_201_CREATED
)
def add_guardian(
    student_id: int,
    payload: GuardianIn,
    db: DbSession,
    actor: Actor = Depends(require_permission("guardians:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Link a guardian to a student."""
    return StudentService(db).add_guardian(actor, scope, student_id, payload)


@router.delete("/{student_id}/guardians/{guardian_id}", response_model=StudentDetail)
def remove_guardian(
    student_id: int,
    guardian_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("guardians:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> StudentDetail:
    """Unlink a guardian."""
    return StudentService(db).remove_guardian(actor, scope, student_id, guardian_id)


@router.post(
    "/{student_id}/documents", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED
)
def upload_document(
    student_id: int,
    db: DbSession,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    actor: Actor = Depends(require_permission("documents:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> DocumentPublic:
    """Upload a PDF or image for a student."""
    data = file.file.read(get_settings().max_upload_bytes + 1)
    return StudentService(db).add_document(
        actor,
        scope,
        student_id,
        doc_type=doc_type,
        original_name=file.filename,
        data=data,
    )


@router.get("/{student_id}/documents/{document_id}")
def download_document(
    student_id: int,
    document_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("documents:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> FileResponse:
    """Download a student document."""
    path, media_type, filename = StudentService(db).document_path(
        actor, scope, student_id, document_id
    )
    return FileResponse(path, media_type=media_type, filename=filename)


@router.delete("/{student_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    student_id: int,
    document_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("documents:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a document."""
    StudentService(db).delete_document(actor, scope, student_id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
