"""Subjects, courses, and batches."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.academics import Batch, Course, Subject
from app.schemas.common import Page
from app.schemas.records import (
    BatchCreate,
    BatchDetail,
    BatchPublic,
    BatchTeacherCreate,
    BatchUpdate,
    CourseCreate,
    CoursePublic,
    CourseUpdate,
    SubjectCreate,
    SubjectPublic,
    SubjectUpdate,
)
from app.services.academic_service import AcademicService

router = APIRouter(tags=["academics"])

_SUBJECT_SORT = {"name": Subject.name, "code": Subject.code}
_COURSE_SORT = {"name": Course.name, "level": Course.level, "created_at": Course.created_at}
_BATCH_SORT = {"name": Batch.name, "start_date": Batch.start_date, "created_at": Batch.created_at}


@router.get("/subjects", response_model=Page[SubjectPublic])
def list_subjects(
    db: DbSession,
    actor: Actor = Depends(require_permission("subjects:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[SubjectPublic]:
    """List subjects."""
    return AcademicService(db).list_subjects(
        scope,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _SUBJECT_SORT, "name"),
    )


@router.post("/subjects", response_model=SubjectPublic, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("subjects:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SubjectPublic:
    """Create a subject."""
    return AcademicService(db).create_subject(actor, scope, payload)


@router.patch("/subjects/{subject_id}", response_model=SubjectPublic)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("subjects:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> SubjectPublic:
    """Update a subject."""
    return AcademicService(db).update_subject(actor, scope, subject_id, payload)


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("subjects:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a subject."""
    AcademicService(db).delete_subject(actor, scope, subject_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/courses", response_model=Page[CoursePublic])
def list_courses(
    db: DbSession,
    actor: Actor = Depends(require_permission("courses:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[CoursePublic]:
    """List courses."""
    return AcademicService(db).list_courses(
        actor,
        scope,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _COURSE_SORT, "name"),
    )


@router.post("/courses", response_model=CoursePublic, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("courses:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> CoursePublic:
    """Create a course."""
    return AcademicService(db).create_course(actor, scope, payload)


@router.get("/courses/{course_id}", response_model=CoursePublic)
def get_course(
    course_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("courses:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> CoursePublic:
    """Fetch one course."""
    return AcademicService(db).get_course(actor, scope, course_id)


@router.patch("/courses/{course_id}", response_model=CoursePublic)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("courses:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> CoursePublic:
    """Update a course."""
    return AcademicService(db).update_course(actor, scope, course_id, payload)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("courses:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a course."""
    AcademicService(db).delete_course(actor, scope, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/batches", response_model=Page[BatchPublic])
def list_batches(
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[BatchPublic]:
    """List batches with seat counts."""
    return AcademicService(db).list_batches(
        actor,
        scope,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _BATCH_SORT, "name"),
    )


@router.post("/batches", response_model=BatchDetail, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BatchDetail:
    """Create a batch."""
    return AcademicService(db).create_batch(actor, scope, payload)


@router.get("/batches/{batch_id}", response_model=BatchDetail)
def get_batch(
    batch_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BatchDetail:
    """Fetch one batch, its teachers, and its seat counts."""
    return AcademicService(db).get_batch(actor, scope, batch_id)


@router.patch("/batches/{batch_id}", response_model=BatchDetail)
def update_batch(
    batch_id: int,
    payload: BatchUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BatchDetail:
    """Update a batch, including its capacity."""
    return AcademicService(db).update_batch(actor, scope, batch_id, payload)


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a batch that has no open seats."""
    AcademicService(db).delete_batch(actor, scope, batch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/batches/{batch_id}/teachers", response_model=BatchDetail, status_code=status.HTTP_201_CREATED
)
def assign_teacher(
    batch_id: int,
    payload: BatchTeacherCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BatchDetail:
    """Assign a teacher to a batch."""
    return AcademicService(db).assign_teacher(actor, scope, batch_id, payload)


@router.delete("/batches/{batch_id}/teachers/{staff_id}", response_model=BatchDetail)
def remove_teacher(
    batch_id: int,
    staff_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("batches:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> BatchDetail:
    """Remove a teacher assignment."""
    return AcademicService(db).remove_teacher(actor, scope, batch_id, staff_id)
