"""Inquiries, follow-ups, and conversion into an admission."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.models.academics import Course
from app.models.people import Inquiry, InquiryFollowup
from app.repositories.records import InquiryRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.records import (
    ConvertInquiry,
    FollowupCreate,
    FollowupPublic,
    InquiryCreate,
    InquiryDetail,
    InquiryPublic,
    InquiryUpdate,
    StudentCreate,
    StudentDetail,
)
from app.services.audit_service import AuditService
from app.services.enrollment_service import EnrollmentService
from app.services.guards import (
    clean_phone,
    ensure_branch,
    not_found,
    snapshot,
    soft_delete,
    stamp_new,
    stamp_update,
)
from app.services.student_service import StudentService, to_student_detail
from app.services.transactions import commit_or_conflict

_FIELDS = (
    "name",
    "phone",
    "email",
    "course_interest_id",
    "source",
    "status",
    "assigned_to",
    "follow_up_date",
    "notes",
)


class InquiryService:
    """Tracks a lead until it is converted, lost, or archived."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.inquiries = InquiryRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    def list_inquiries(
        self,
        scope: BranchScope,
        *,
        q: str | None,
        status: str | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[InquiryPublic]:
        """Return one page of inquiries in the caller's branches."""
        rows, total = self.inquiries.list_inquiries(
            scope,
            q=q,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            order=order,
        )
        return Page(
            items=[to_inquiry(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_inquiry(self, scope: BranchScope, inquiry_id: int) -> InquiryDetail:
        """Return one inquiry and its follow-up notes."""
        return to_inquiry_detail(self._visible(scope, inquiry_id))

    def create_inquiry(
        self, actor: Actor, scope: BranchScope, payload: InquiryCreate
    ) -> InquiryDetail:
        """Record a new lead."""
        ensure_branch(scope, payload.branch_id)
        self._check_course(scope, payload.branch_id, payload.course_interest_id)
        self._check_assignee(payload.assigned_to)
        inquiry = Inquiry(
            branch_id=payload.branch_id,
            name=payload.name.strip(),
            phone=clean_phone(payload.phone),
            email=_email(payload.email),
            course_interest_id=payload.course_interest_id,
            source=payload.source,
            status="new",
            assigned_to=payload.assigned_to,
            follow_up_date=payload.follow_up_date,
            notes=_text(payload.notes),
        )
        stamp_new(inquiry, actor.id)
        self.session.add(inquiry)
        self.session.flush()
        self.audit.record(
            action="create",
            entity="inquiry",
            entity_id=inquiry.id,
            actor_id=actor.id,
            branch_id=inquiry.branch_id,
            new_values=snapshot(inquiry, _FIELDS),
        )
        commit_or_conflict(self.session)
        return to_inquiry_detail(self._visible(scope, inquiry.id))

    def update_inquiry(
        self, actor: Actor, scope: BranchScope, inquiry_id: int, payload: InquiryUpdate
    ) -> InquiryDetail:
        """Update a lead. Conversion has its own action and cannot be set here."""
        inquiry = self._visible(scope, inquiry_id)
        if inquiry.status == "converted" or payload.status == "converted":
            raise AppException(
                409,
                "CONFLICT",
                "Use the convert action to turn a lead into a student",
            )
        old = snapshot(inquiry, _FIELDS)
        if payload.name is not None:
            inquiry.name = payload.name.strip()
        if "phone" in payload.model_fields_set:
            inquiry.phone = clean_phone(payload.phone)
        if "email" in payload.model_fields_set:
            inquiry.email = _email(payload.email)
        if "course_interest_id" in payload.model_fields_set:
            self._check_course(scope, inquiry.branch_id, payload.course_interest_id)
            inquiry.course_interest_id = payload.course_interest_id
        if payload.source is not None:
            inquiry.source = payload.source
        if payload.status is not None:
            inquiry.status = payload.status
        if "follow_up_date" in payload.model_fields_set:
            inquiry.follow_up_date = payload.follow_up_date
        if "notes" in payload.model_fields_set:
            inquiry.notes = _text(payload.notes)
        if "assigned_to" in payload.model_fields_set:
            self._check_assignee(payload.assigned_to)
            inquiry.assigned_to = payload.assigned_to
        stamp_update(inquiry, actor.id)
        self.audit.record(
            action="update",
            entity="inquiry",
            entity_id=inquiry.id,
            actor_id=actor.id,
            branch_id=inquiry.branch_id,
            old_values=old,
            new_values=snapshot(inquiry, _FIELDS),
        )
        commit_or_conflict(self.session)
        return to_inquiry_detail(self._visible(scope, inquiry.id))

    def delete_inquiry(self, actor: Actor, scope: BranchScope, inquiry_id: int) -> None:
        """Archive a lead that was not converted."""
        inquiry = self._visible(scope, inquiry_id)
        if inquiry.status == "converted":
            raise AppException(409, "CONFLICT", "A converted inquiry stays on the record")
        soft_delete(inquiry, actor.id)
        self.audit.record(
            action="delete",
            entity="inquiry",
            entity_id=inquiry.id,
            actor_id=actor.id,
            branch_id=inquiry.branch_id,
            old_values={"status": inquiry.status, "name": inquiry.name},
        )
        commit_or_conflict(self.session)

    def add_followup(
        self, actor: Actor, scope: BranchScope, inquiry_id: int, payload: FollowupCreate
    ) -> InquiryDetail:
        """Append a note and, when supplied, the next date to call."""
        inquiry = self._visible(scope, inquiry_id)
        if inquiry.status in {"converted", "lost"}:
            raise AppException(409, "CONFLICT", "This inquiry is already closed")
        note = InquiryFollowup(
            branch_id=inquiry.branch_id,
            inquiry_id=inquiry.id,
            note=payload.note.strip(),
            next_date=payload.next_date,
            created_by=actor.id,
        )
        self.session.add(note)
        if payload.next_date is not None:
            inquiry.follow_up_date = payload.next_date
        if inquiry.status == "new":
            inquiry.status = "contacted"
        stamp_update(inquiry, actor.id)
        self.session.flush()
        self.audit.record(
            action="update",
            entity="inquiry",
            entity_id=inquiry.id,
            actor_id=actor.id,
            branch_id=inquiry.branch_id,
            new_values={"followup": note.note, "status": inquiry.status},
        )
        commit_or_conflict(self.session)
        return to_inquiry_detail(self._visible(scope, inquiry.id))

    def convert(
        self, actor: Actor, scope: BranchScope, inquiry_id: int, payload: ConvertInquiry
    ) -> StudentDetail:
        """Create a student from the lead and, when a batch is chosen, enroll them.

        A full batch waitlists the new student. The inquiry is marked converted
        and cannot be converted again.
        """
        inquiry = self._visible(scope, inquiry_id)
        if inquiry.status == "converted" or inquiry.converted_student_id is not None:
            raise AppException(409, "CONFLICT", "This inquiry was already converted")
        if inquiry.status == "lost":
            raise AppException(409, "CONFLICT", "Reopen the inquiry before converting it")
        if payload.batch_id is not None and not actor.has_permission("enrollment:create"):
            raise AppException(
                403, "FORBIDDEN", "You do not have permission to enroll this student"
            )
        first, last = _names(inquiry.name, payload.first_name, payload.last_name)
        students = StudentService(self.session)
        student = students._insert(
            actor,
            scope,
            StudentCreate(
                branch_id=inquiry.branch_id,
                first_name=first,
                last_name=last,
                grade_level=payload.grade_level,
                admission_date=payload.admission_date,
                guardian=None,
            ),
        )
        if inquiry.phone or inquiry.email:
            from app.schemas.records import GuardianIn

            students._add_guardian(
                actor,
                student,
                GuardianIn(
                    full_name=inquiry.name,
                    relationship="Contact",
                    phone=inquiry.phone,
                    email=inquiry.email,
                    is_primary=True,
                ),
            )
        enrollment_status = None
        if payload.batch_id is not None:
            seated = EnrollmentService(self.session)._seat(
                actor,
                scope,
                student_id=student.id,
                batch_id=payload.batch_id,
                enrolled_on=payload.admission_date or student.admission_date,
            )
            enrollment_status = seated.status
        inquiry.status = "converted"
        inquiry.converted_student_id = student.id
        stamp_update(inquiry, actor.id)
        self.audit.record(
            action="convert",
            entity="inquiry",
            entity_id=inquiry.id,
            actor_id=actor.id,
            branch_id=inquiry.branch_id,
            new_values={
                "student_id": student.id,
                "admission_no": student.admission_no,
                "enrollment_status": enrollment_status,
            },
        )
        commit_or_conflict(self.session)
        loaded = students._visible(actor, scope, student.id)
        return to_student_detail(loaded)

    def _visible(self, scope: BranchScope, inquiry_id: int) -> Inquiry:
        inquiry = self.inquiries.get_inquiry(inquiry_id, scope)
        if inquiry is None:
            raise not_found("Inquiry")
        return inquiry

    def _check_course(self, scope: BranchScope, branch_id: int, course_id: int | None) -> None:
        if course_id is None:
            return
        course = self.session.get(Course, course_id)
        if (
            course is None
            or course.deleted_at is not None
            or course.branch_id != branch_id
            or (not scope.unrestricted and course.branch_id not in scope.branch_ids)
        ):
            raise not_found("Course")

    def _check_assignee(self, user_id: int | None) -> None:
        if user_id is None:
            return
        user = self.users.get(user_id)
        if user is None or user.status != "active":
            raise not_found("User")


def to_inquiry(row: Inquiry) -> InquiryPublic:
    """Map a lead, including the course name when one was recorded."""
    return InquiryPublic(
        id=row.id,
        branch_id=row.branch_id,
        name=row.name,
        phone=row.phone,
        email=row.email,
        course_interest_id=row.course_interest_id,
        course_name=row.course.name if row.course is not None else None,
        source=row.source,
        status=row.status,
        assigned_to=row.assigned_to,
        follow_up_date=row.follow_up_date,
        notes=row.notes,
        converted_student_id=row.converted_student_id,
        created_at=row.created_at,
    )


def to_inquiry_detail(row: Inquiry) -> InquiryDetail:
    """Map a lead and its notes, oldest first."""
    notes = sorted(row.followups, key=lambda item: item.id)
    base = to_inquiry(row).model_dump()
    return InquiryDetail(
        **base,
        followups=[
            FollowupPublic(
                id=item.id,
                note=item.note,
                next_date=item.next_date,
                created_at=item.created_at,
                created_by=item.created_by,
            )
            for item in notes
        ],
    )


def _names(full: str, first: str | None, last: str | None) -> tuple[str, str]:
    if first and last:
        return first.strip(), last.strip()
    parts = full.split()
    if len(parts) == 1:
        return parts[0], "Student"
    return parts[0], " ".join(parts[1:])


def _email(value) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower() or None


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
