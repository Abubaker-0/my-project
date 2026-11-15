"""Closed sets of values enforced by the product rules.

Models, serializers, services, and the React client all use these codes.
Do not add gender, payment, attendance, or contract options here without a
matching business-rule change.
"""

from django.db import models


class Gender(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'


class Role(models.TextChoices):
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    CENTER_MANAGER = 'center_manager', 'Center Manager'
    FINANCE_MANAGER = 'finance_manager', 'Finance Manager'
    TEACHER = 'teacher', 'Teacher'
    STUDENT = 'student', 'Student'


class ContractType(models.TextChoices):
    YEARLY = 'yearly', 'Yearly'
    SIX_MONTHS = 'six_months', 'Six Months'


class ContractStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    TERMINATED = 'terminated', 'Terminated'


class SalaryType(models.TextChoices):
    HOURLY = 'hourly', 'Hourly'
    MONTHLY = 'monthly', 'Monthly'


class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Cash'
    BANK = 'bank', 'Bank'


class CourseStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    COMPLETED = 'completed', 'Completed'


class EnrollmentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    REJECTED = 'rejected', 'Rejected'
    WITHDRAWN = 'withdrawn', 'Withdrawn'
    COMPLETED = 'completed', 'Completed'


class EnrollmentSource(models.TextChoices):
    SELF = 'self', 'Self'
    MANUAL = 'manual', 'Manual'


class AttendanceStatus(models.TextChoices):
    PRESENT = 'present', 'Present'
    ABSENT = 'absent', 'Absent'


class InvoiceStatus(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PARTIAL = 'partial', 'Partial'
    PAID = 'paid', 'Paid'
    REFUNDED = 'refunded', 'Refunded'
    CANCELLED = 'cancelled', 'Cancelled'


class InstallmentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
    PAID = 'paid', 'Paid'
    OVERDUE = 'overdue', 'Overdue'


class ScholarshipType(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage'
    FIXED = 'fixed', 'Fixed Amount'


class RefundStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class ReportStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED_TO_MANAGER = 'submitted_to_manager', 'Submitted to Manager'
    RETURNED = 'returned', 'Returned'
    SENT_TO_SUPER_ADMIN = 'sent_to_super_admin', 'Sent to Super Admin'


# Staff who must hold a contract. Students and the super admin never do.
STAFF_CONTRACT_ROLES = {
    Role.CENTER_MANAGER,
    Role.FINANCE_MANAGER,
    Role.TEACHER,
}

OPEN_ENROLLMENT = {EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE}

ROLE_GROUP = {
    Role.SUPER_ADMIN: 'Super Admin',
    Role.CENTER_MANAGER: 'Center Manager',
    Role.FINANCE_MANAGER: 'Finance Manager',
    Role.TEACHER: 'Teacher',
    Role.STUDENT: 'Student',
}
