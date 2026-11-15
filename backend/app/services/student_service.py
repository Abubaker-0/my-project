"""Student records, guardians, documents, and campus transfers."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.models.people import Guardian, Student, StudentDocument, StudentGuardian
from app.models.user import User
from app.repositories.branch_repository import BranchRepository
from app.repositories.records import BatchRepository, StudentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.records import (
    DocumentPublic,
    GuardianIn,
    GuardianPublic,
    StudentCreate,
    StudentDetail,
    StudentPublic,
    StudentUpdate,
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
from app.services.numbering import NumberingService
from app.services.storage import absolute_path, save_document
from app.services.transactions import commit_or_conflict

_STUDENT_FIELDS = (
    "first_name",
    "last_name",
    "dob",
    "gender",
    "address",
    "school_name",
    "grade_level",
    "status",
    "admission_date",
    "branch_id",
)


class StudentService:
    """Admits students and keeps guardians and documents on the same transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.students = StudentRepository(session)
        self.branches = BranchRepository(session)
        self.users = UserRepository(session)
        self.numbers = NumberingService(session)
        self.audit = AuditService(session)

    def list_students(
        self,
        actor: Actor,
        scope: BranchScope,
        *,
        q: str | None,
        status: str | None,
        page: int,
        page_size: int,
        order,
    ) -> Page[StudentPublic]:
        """Return one page of students inside the caller's branch and ownership scope."""
        rows, total = self.students.list_students(
            scope,
            actor,
            q=q,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            order=order,
        )
        return Page(
            items=[to_student(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_student(self, actor: Actor, scope: BranchScope, student_id: int) -> StudentDetail:
        """Return one student with guardians and documents."""
        student = self._visible(actor, scope, student_id)
        return to_student_detail(student)

    def create_student(
        self, actor: Actor, scope: BranchScope, payload: StudentCreate
    ) -> StudentDetail:
        """Admit a student, allocating the next admission number for the campus."""
        student = self._insert(actor, scope, payload)
        commit_or_conflict(self.session)
        loaded = self._visible(actor, scope, student.id)
        return to_student_detail(loaded)

    def update_student(
        self, actor: Actor, scope: BranchScope, student_id: int, payload: StudentUpdate
    ) -> StudentDetail:
        """Update profile fields. Leaving active status frees any open seats."""
        student = self._visible(actor, scope, student_id)
        old = snapshot(student, _STUDENT_FIELDS)
        self._apply_profile(student, payload)
        if old["status"] == "active" and student.status != "active":
            self._release_seats(actor, student, "Student is no longer active")
        stamp_update(student, actor.id)
        self.audit.record(
            action="update",
            entity="student",
            entity_id=student.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            old_values=old,
            new_values=snapshot(student, _STUDENT_FIELDS),
        )
        commit_or_conflict(self.session)
        return to_student_detail(self._visible(actor, scope, student.id))

    def delete_student(self, actor: Actor, scope: BranchScope, student_id: int) -> None:
        """Archive a student and free their open seats. The row stays in the database."""
        student = self._visible(actor, scope, student_id)
        self._release_seats(actor, student, "Student archived")
        old = snapshot(student, ("status", "admission_no"))
        student.status = "dropped"
        soft_delete(student, actor.id)
        self.audit.record(
            action="delete",
            entity="student",
            entity_id=student.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            old_values=old,
            new_values={"status": "dropped", "deleted_at": student.deleted_at.isoformat()},
        )
        commit_or_conflict(self.session)

    def transfer_branch(
        self, actor: Actor, scope: BranchScope, student_id: int, branch_id: int
    ) -> StudentDetail:
        """Move a student to another campus and close seats at the old one."""
        student = self._visible(actor, scope, student_id)
        ensure_branch(scope, branch_id)
        if student.branch_id == branch_id:
            raise AppException(409, "CONFLICT", "The student is already at that campus")
        target = self.branches.get_visible(branch_id, scope)
        if target is None or target.status != "active":
            raise not_found("Branch")
        old_branch = student.branch_id
        self._release_seats(actor, student, "Transferred to another campus")
        student.branch_id = branch_id
        stamp_update(student, actor.id)
        for document in student.documents:
            document.branch_id = branch_id
            stamp_update(document, actor.id)
        for link in list(student.guardian_links):
            guardian = link.guardian
            if guardian.deleted_at is None and _guardian_can_follow(
                guardian, student.id, branch_id
            ):
                guardian.branch_id = branch_id
                stamp_update(guardian, actor.id)
        self.audit.record(
            action="transfer",
            entity="student",
            entity_id=student.id,
            actor_id=actor.id,
            branch_id=branch_id,
            old_values={"branch_id": old_branch},
            new_values={"branch_id": branch_id},
        )
        commit_or_conflict(self.session)
        return to_student_detail(self._visible(actor, scope, student.id))

    def add_guardian(
        self, actor: Actor, scope: BranchScope, student_id: int, payload: GuardianIn
    ) -> StudentDetail:
        """Attach a guardian. The first primary contact replaces any previous one."""
        student = self._visible(actor, scope, student_id)
        self._add_guardian(actor, student, payload)
        self.audit.record(
            action="update",
            entity="student",
            entity_id=student.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            new_values={"guardian": payload.full_name},
        )
        commit_or_conflict(self.session)
        return to_student_detail(self._visible(actor, scope, student.id))

    def remove_guardian(
        self, actor: Actor, scope: BranchScope, student_id: int, guardian_id: int
    ) -> StudentDetail:
        """Unlink a guardian. A guardian with no remaining students is archived."""
        student = self._visible(actor, scope, student_id)
        link = self.students.link(student.id, guardian_id)
        if link is None:
            raise not_found("Guardian")
        guardian = link.guardian
        self.session.delete(link)
        self.session.flush()
        remaining = self.session.scalar(
            select(StudentGuardian.student_id).where(StudentGuardian.guardian_id == guardian.id)
        )
        if remaining is None:
            guardian.user_id = None
            soft_delete(guardian, actor.id)
        self.audit.record(
            action="update",
            entity="student",
            entity_id=student.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            old_values={"guardian_id": guardian_id},
            new_values={"guardian_id": None},
        )
        commit_or_conflict(self.session)
        return to_student_detail(self._visible(actor, scope, student.id))

    def add_document(
        self,
        actor: Actor,
        scope: BranchScope,
        student_id: int,
        *,
        doc_type: str,
        original_name: str | None,
        data: bytes,
    ) -> DocumentPublic:
        """Store a validated file and record it against the student."""
        student = self._visible(actor, scope, student_id)
        allowed = {"birth_certificate", "photo", "report", "id_copy", "other"}
        if doc_type not in allowed:
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Choose a document type",
                details=[{"field": "doc_type", "message": "Unsupported document type"}],
            )
        file_name, stored_path, content_type = save_document(data, original_name)
        document = StudentDocument(
            branch_id=student.branch_id,
            student_id=student.id,
            doc_type=doc_type,
            file_name=file_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=len(data),
            uploaded_by=actor.id,
        )
        stamp_new(document, actor.id)
        self.session.add(document)
        if doc_type == "photo":
            student.photo_path = stored_path
            stamp_update(student, actor.id)
        self.session.flush()
        self.audit.record(
            action="upload",
            entity="student_document",
            entity_id=document.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            new_values={"student_id": student.id, "doc_type": doc_type, "file_name": file_name},
        )
        commit_or_conflict(self.session)
        return to_document(document)

    def delete_document(
        self, actor: Actor, scope: BranchScope, student_id: int, document_id: int
    ) -> None:
        """Archive a document row. The file remains so the history can be restored."""
        student = self._visible(actor, scope, student_id)
        document = self.students.document(document_id, student.id)
        if document is None:
            raise not_found("Document")
        soft_delete(document, actor.id)
        if student.photo_path == document.stored_path:
            student.photo_path = None
            stamp_update(student, actor.id)
        self.audit.record(
            action="delete",
            entity="student_document",
            entity_id=document.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            old_values={"file_name": document.file_name, "doc_type": document.doc_type},
        )
        commit_or_conflict(self.session)

    def document_path(self, actor: Actor, scope: BranchScope, student_id: int, document_id: int):
        """Return the file path, media type, and download name for one document."""
        student = self._visible(actor, scope, student_id)
        document = self.students.document(document_id, student.id)
        if document is None:
            raise not_found("Document")
        return absolute_path(document.stored_path), document.content_type, document.file_name

    def _insert(self, actor: Actor, scope: BranchScope, payload: StudentCreate) -> Student:
        ensure_branch(scope, payload.branch_id)
        branch = self.branches.get_visible(payload.branch_id, scope)
        if branch is None or branch.status != "active":
            raise not_found("Branch")
        admission_no = self.numbers.allocate(
            branch.id,
            "admission",
            f"{branch.code}-{date.today().year}-",
            actor.id,
        )
        student = Student(
            branch_id=branch.id,
            admission_no=admission_no,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            dob=payload.dob,
            gender=payload.gender,
            address=_blank(payload.address),
            school_name=_blank(payload.school_name),
            grade_level=_blank(payload.grade_level),
            status=payload.status,
            admission_date=payload.admission_date or date.today(),
        )
        stamp_new(student, actor.id)
        self.session.add(student)
        self.session.flush()
        if payload.guardian is not None:
            self._add_guardian(actor, student, payload.guardian)
        self.audit.record(
            action="create",
            entity="student",
            entity_id=student.id,
            actor_id=actor.id,
            branch_id=student.branch_id,
            new_values=snapshot(student, _STUDENT_FIELDS) | {"admission_no": admission_no},
        )
        return student

    def _add_guardian(self, actor: Actor, student: Student, payload: GuardianIn) -> Guardian:
        user = self._guardian_user(payload.user_id)
        guardian = Guardian(
            branch_id=student.branch_id,
            user_id=user.id if user is not None else None,
            full_name=payload.full_name.strip(),
            relationship_name=payload.relationship.strip(),
            phone=clean_phone(payload.phone),
            email=str(payload.email).strip().lower() if payload.email else None,
            occupation=_blank(payload.occupation),
            address=_blank(payload.address),
        )
        stamp_new(guardian, actor.id)
        self.session.add(guardian)
        self.session.flush()
        if payload.is_primary:
            for link in student.guardian_links:
                link.is_primary = False
        link = StudentGuardian(
            student_id=student.id,
            guardian_id=guardian.id,
            is_primary=payload.is_primary,
            can_pay=payload.can_pay,
            can_view=payload.can_view,
            created_by=actor.id,
        )
        self.session.add(link)
        self.session.flush()
        return guardian

    def _guardian_user(self, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        user = self.users.get(user_id)
        if user is None or user.status != "active":
            raise not_found("User")
        taken = self.session.scalar(
            select(Guardian.id).where(Guardian.user_id == user.id, Guardian.deleted_at.is_(None))
        )
        if taken is not None:
            raise AppException(409, "CONFLICT", "That login is already linked to a guardian")
        return user

    def _visible(self, actor: Actor, scope: BranchScope, student_id: int) -> Student:
        student = self.students.get_student(student_id, scope, actor)
        if student is None:
            raise not_found("Student")
        return student

    def _apply_profile(self, student: Student, payload: StudentUpdate) -> None:
        if payload.first_name is not None:
            student.first_name = payload.first_name.strip()
        if payload.last_name is not None:
            student.last_name = payload.last_name.strip()
        if "dob" in payload.model_fields_set:
            student.dob = payload.dob
        if payload.gender is not None:
            student.gender = payload.gender
        if "address" in payload.model_fields_set:
            student.address = _blank(payload.address)
        if "school_name" in payload.model_fields_set:
            student.school_name = _blank(payload.school_name)
        if "grade_level" in payload.model_fields_set:
            student.grade_level = _blank(payload.grade_level)
        if payload.status is not None:
            student.status = payload.status
        if payload.admission_date is not None:
            student.admission_date = payload.admission_date

    def _release_seats(self, actor: Actor, student: Student, reason: str) -> None:
        seats = EnrollmentService(self.session)
        open_seats = BatchRepository(self.session).open_for_student(student.id)
        for enrollment in open_seats:
            seats._withdraw(actor, enrollment, reason, batch_locked=False)


def _guardian_can_follow(guardian: Guardian, student_id: int, branch_id: int) -> bool:
    for link in guardian.student_links:
        if link.student_id == student_id:
            continue
        other = link.student
        if other.deleted_at is None and other.branch_id != branch_id:
            return False
    return True


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def to_student(row: Student) -> StudentPublic:
    """Map the columns shown in the student list."""
    return StudentPublic(
        id=row.id,
        branch_id=row.branch_id,
        admission_no=row.admission_no,
        first_name=row.first_name,
        last_name=row.last_name,
        full_name=row.full_name,
        dob=row.dob,
        gender=row.gender,
        grade_level=row.grade_level,
        school_name=row.school_name,
        status=row.status,
        admission_date=row.admission_date,
        created_at=row.created_at,
    )


def to_student_detail(row: Student) -> StudentDetail:
    """Map a student plus guardians and documents."""
    base = to_student(row).model_dump()
    return StudentDetail(
        **base,
        address=row.address,
        guardians=[
            _guardian_public(link)
            for link in row.guardian_links
            if link.guardian.deleted_at is None
        ],
        documents=[to_document(doc) for doc in row.documents if doc.deleted_at is None],
    )


def to_document(row: StudentDocument) -> DocumentPublic:
    """Map one stored file."""
    return DocumentPublic(
        id=row.id,
        student_id=row.student_id,
        doc_type=row.doc_type,
        file_name=row.file_name,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        created_at=row.created_at,
    )


def _guardian_public(link: StudentGuardian) -> GuardianPublic:
    guardian = link.guardian
    return GuardianPublic(
        id=guardian.id,
        full_name=guardian.full_name,
        relationship=guardian.relationship_name,
        phone=guardian.phone,
        email=guardian.email,
        occupation=guardian.occupation,
        address=guardian.address,
        is_primary=link.is_primary,
        can_pay=link.can_pay,
        can_view=link.can_view,
        user_id=guardian.user_id,
    )
