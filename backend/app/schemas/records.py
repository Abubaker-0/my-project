"""Request and response shapes for campuses, academics, people, and enrollment."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.common import APIModel, UtcDateTime

StudentStatus = Literal["active", "graduated", "dropped", "suspended"]
Gender = Literal["female", "male", "other", "unspecified"]
RoomStatus = Literal["active", "inactive"]
CourseStatus = Literal["active", "inactive"]
BatchStatus = Literal["planned", "active", "completed", "cancelled"]
InquiryStatus = Literal["new", "contacted", "qualified", "converted", "lost"]
InquirySource = Literal["walk_in", "phone", "website", "referral", "other"]
EnrollmentStatus = Literal["active", "waitlisted", "withdrawn", "completed"]
TeacherRole = Literal["primary", "assistant"]
DocumentType = Literal["birth_certificate", "photo", "report", "id_copy", "other"]


class BranchCreate(APIModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{1,31}$")
    name: str = Field(min_length=2, max_length=200)
    address: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None


class BranchUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    address: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    status: Literal["active", "inactive"] | None = None


class AcademicYearCreate(APIModel):
    branch_id: int
    name: str = Field(min_length=2, max_length=100)
    start_date: date
    end_date: date
    is_current: bool = False


class AcademicYearUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None


class AcademicYearPublic(APIModel):
    id: int
    branch_id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool
    created_at: UtcDateTime


class TermCreate(APIModel):
    name: str = Field(min_length=2, max_length=100)
    start_date: date
    end_date: date


class TermUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    start_date: date | None = None
    end_date: date | None = None


class TermPublic(APIModel):
    id: int
    branch_id: int
    academic_year_id: int
    name: str
    start_date: date
    end_date: date


class AcademicYearDetail(AcademicYearPublic):
    terms: list[TermPublic]


class RoomCreate(APIModel):
    branch_id: int
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1, le=10000)
    status: RoomStatus = "active"


class RoomUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    capacity: int | None = Field(default=None, ge=1, le=10000)
    status: RoomStatus | None = None


class RoomPublic(APIModel):
    id: int
    branch_id: int
    name: str
    capacity: int
    status: str
    created_at: UtcDateTime


class SubjectCreate(APIModel):
    branch_id: int
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")
    name: str = Field(min_length=2, max_length=200)


class SubjectUpdate(APIModel):
    code: str | None = Field(
        default=None, min_length=2, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$"
    )
    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: CourseStatus | None = None


class SubjectPublic(APIModel):
    id: int
    branch_id: int
    code: str
    name: str
    status: str


class CourseCreate(APIModel):
    branch_id: int
    subject_id: int
    name: str = Field(min_length=2, max_length=200)
    level: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    duration_weeks: int = Field(ge=1, le=104)
    status: CourseStatus = "active"


class CourseUpdate(APIModel):
    subject_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    level: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    duration_weeks: int | None = Field(default=None, ge=1, le=104)
    status: CourseStatus | None = None


class CoursePublic(APIModel):
    id: int
    branch_id: int
    subject_id: int
    subject_name: str
    name: str
    level: str
    description: str | None
    duration_weeks: int
    status: str
    created_at: UtcDateTime


class BatchCreate(APIModel):
    branch_id: int
    course_id: int
    term_id: int
    room_id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    start_date: date
    end_date: date
    capacity: int = Field(ge=1, le=10000)
    status: BatchStatus = "planned"


class BatchUpdate(APIModel):
    room_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    capacity: int | None = Field(default=None, ge=1, le=10000)
    status: BatchStatus | None = None


class BatchTeacherCreate(APIModel):
    user_id: int
    role: TeacherRole = "primary"


class BatchTeacherPublic(APIModel):
    staff_id: int
    user_id: int
    full_name: str
    employee_no: str
    role: str


class BatchPublic(APIModel):
    id: int
    branch_id: int
    course_id: int
    course_name: str
    term_id: int
    term_name: str
    room_id: int | None
    room_name: str | None
    name: str
    start_date: date
    end_date: date
    capacity: int
    status: str
    active_count: int
    waitlist_count: int
    created_at: UtcDateTime


class BatchDetail(BatchPublic):
    teachers: list[BatchTeacherPublic]


class GuardianIn(APIModel):
    full_name: str = Field(min_length=2, max_length=200)
    relationship: str = Field(min_length=2, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    occupation: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=2000)
    is_primary: bool = False
    can_pay: bool = True
    can_view: bool = True
    user_id: int | None = None


class GuardianPublic(APIModel):
    id: int
    full_name: str
    relationship: str
    phone: str | None
    email: str | None
    occupation: str | None
    address: str | None
    is_primary: bool
    can_pay: bool
    can_view: bool
    user_id: int | None


class StudentCreate(APIModel):
    branch_id: int
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    dob: date | None = None
    gender: Gender = "unspecified"
    address: str | None = Field(default=None, max_length=2000)
    school_name: str | None = Field(default=None, max_length=200)
    grade_level: str | None = Field(default=None, max_length=64)
    status: StudentStatus = "active"
    admission_date: date | None = None
    guardian: GuardianIn | None = None


class StudentUpdate(APIModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    dob: date | None = None
    gender: Gender | None = None
    address: str | None = Field(default=None, max_length=2000)
    school_name: str | None = Field(default=None, max_length=200)
    grade_level: str | None = Field(default=None, max_length=64)
    status: StudentStatus | None = None
    admission_date: date | None = None


class StudentTransfer(APIModel):
    branch_id: int


class StudentPublic(APIModel):
    id: int
    branch_id: int
    admission_no: str
    first_name: str
    last_name: str
    full_name: str
    dob: date | None
    gender: str
    grade_level: str | None
    school_name: str | None
    status: str
    admission_date: date
    created_at: UtcDateTime


class DocumentPublic(APIModel):
    id: int
    student_id: int
    doc_type: str
    file_name: str
    content_type: str
    size_bytes: int
    created_at: UtcDateTime


class StudentDetail(StudentPublic):
    address: str | None
    guardians: list[GuardianPublic]
    documents: list[DocumentPublic]


class InquiryCreate(APIModel):
    branch_id: int
    name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    course_interest_id: int | None = None
    source: InquirySource = "walk_in"
    follow_up_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    assigned_to: int | None = None


class InquiryUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    course_interest_id: int | None = None
    source: InquirySource | None = None
    status: InquiryStatus | None = None
    follow_up_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    assigned_to: int | None = None


class InquiryPublic(APIModel):
    id: int
    branch_id: int
    name: str
    phone: str | None
    email: str | None
    course_interest_id: int | None
    course_name: str | None
    source: str
    status: str
    assigned_to: int | None
    follow_up_date: date | None
    notes: str | None
    converted_student_id: int | None
    created_at: UtcDateTime


class FollowupCreate(APIModel):
    note: str = Field(min_length=1, max_length=4000)
    next_date: date | None = None


class FollowupPublic(APIModel):
    id: int
    note: str
    next_date: date | None
    created_at: UtcDateTime
    created_by: int | None


class InquiryDetail(InquiryPublic):
    followups: list[FollowupPublic]


class ConvertInquiry(APIModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    grade_level: str | None = Field(default=None, max_length=64)
    admission_date: date | None = None
    batch_id: int | None = None


class EnrollmentCreate(APIModel):
    student_id: int
    batch_id: int
    enrolled_on: date | None = None


class EnrollmentWithdraw(APIModel):
    reason: str = Field(min_length=2, max_length=500)


class EnrollmentTransfer(APIModel):
    batch_id: int


class EnrollmentPublic(APIModel):
    id: int
    branch_id: int
    student_id: int
    student_name: str
    admission_no: str
    batch_id: int
    batch_name: str
    course_name: str
    status: str
    waitlist_position: int | None
    enrolled_on: date
    withdrawal_reason: str | None
    created_at: UtcDateTime
