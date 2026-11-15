"""Import every model so metadata and Alembic see the full schema."""

from app.models.academics import (
    AcademicYear,
    Batch,
    BatchTeacher,
    Course,
    NumberSequence,
    Room,
    Staff,
    Subject,
    Term,
)
from app.models.audit import AuditLog
from app.models.branch import Branch
from app.models.enrollment import Enrollment
from app.models.operations import (
    AttendanceMark,
    AttendanceSheet,
    ClassSession,
    FeePlan,
    Invoice,
    InvoiceLine,
    Payment,
)
from app.models.people import (
    Guardian,
    Inquiry,
    InquiryFollowup,
    Student,
    StudentDocument,
    StudentGuardian,
)
from app.models.rbac import Permission, Role, UserRole, role_permissions
from app.models.token import PasswordReset, RefreshToken
from app.models.user import User

__all__ = [
    "AcademicYear",
    "AttendanceMark",
    "AttendanceSheet",
    "AuditLog",
    "ClassSession",
    "Batch",
    "BatchTeacher",
    "Branch",
    "Course",
    "Enrollment",
    "FeePlan",
    "Guardian",
    "Inquiry",
    "Invoice",
    "InvoiceLine",
    "InquiryFollowup",
    "NumberSequence",
    "PasswordReset",
    "Payment",
    "Permission",
    "RefreshToken",
    "Role",
    "Room",
    "Staff",
    "Student",
    "StudentDocument",
    "StudentGuardian",
    "Subject",
    "Term",
    "User",
    "UserRole",
    "role_permissions",
]
