"""Enrollment rules.

A student may join several courses in their own center and none outside it.
Self-enrollment checks the center setting, capacity, duplicates, and schedule
clashes. The center manager can enroll manually when self-enrollment is
turned off, but cannot bypass capacity, the center boundary, or a full class.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.services import assert_operational
from apps.classes.services import assert_student_free
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import OPEN_ENROLLMENT, CourseStatus, EnrollmentSource, EnrollmentStatus, Role
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.common.models import AuditLog
from apps.courses.models import Course
from apps.enrollments.models import Enrollment


def enroll(*, student, course, course_class, actor, source, request=None):
    """Enroll one student. Capacity is locked so two requests cannot overfill a course."""

    if student.role != Role.STUDENT or not student.is_active:
        raise BusinessRuleError('Only an active student can be enrolled.')
    if course.is_deleted or course_class.is_deleted or not course_class.is_active:
        raise BusinessRuleError('This class is not open.')
    if course_class.course_id != course.id or course_class.center_id != course.center_id:
        raise BusinessRuleError('The class does not belong to this course.')
    # Cross-center enrollment is a security event, whether the student or a manager attempts it.
    if student.center_id != course.center_id:
        write_audit(
            request,
            'security.cross_center',
            f'{actor.username} attempted to enroll {student.username} into center {course.center_id}.',
            user=actor,
            entity='course',
            entity_id=course.id,
            level=AuditLog.Level.SECURITY,
        )
        raise PermissionDenied('A student cannot enroll in a course at another center.')
    if Enrollment.objects.filter(student=student, status__in=OPEN_ENROLLMENT).exclude(center_id=course.center_id).exists():
        raise BusinessRuleError('A student cannot be enrolled in two centers at the same time.')
    if course.status != CourseStatus.ACTIVE:
        raise BusinessRuleError('This course is not open for enrollment.')
    if not course.center.is_active or course.center.is_deleted:
        raise BusinessRuleError('This center is not active.')
    existing = Enrollment.objects.filter(student=student, course=course, status__in=OPEN_ENROLLMENT).first()
    if existing:
        raise ConflictError('The student already has an enrollment for this course.')

    settings = course.center.settings
    if source == EnrollmentSource.SELF:
        if actor.role != Role.STUDENT or actor.id != student.id:
            raise PermissionDenied('Students can only enroll themselves.')
        assert_operational(actor)
        if not settings.allow_self_enrollment:
            raise BusinessRuleError('Self-enrollment is turned off. A center manager can enroll the student.')
        status = EnrollmentStatus.PENDING if settings.require_enrollment_approval else EnrollmentStatus.ACTIVE
    elif source == EnrollmentSource.MANUAL:
        if actor.role != Role.CENTER_MANAGER:
            raise PermissionDenied('Only a center manager can enroll a student manually.')
        assert_same_center(actor, course.center, request)
        assert_operational(actor)
        status = EnrollmentStatus.ACTIVE
    else:
        raise BusinessRuleError('Unknown enrollment source.')

    assert_student_free(student, course_class)
    try:
        with transaction.atomic():
            locked = Course.objects.select_for_update().get(pk=course.pk)
            taken = Enrollment.objects.filter(course=locked, status__in=OPEN_ENROLLMENT).count()
            if taken >= locked.capacity:
                raise ConflictError('This course is full.')
            enrollment = Enrollment(
                student=student,
                course=locked,
                course_class=course_class,
                center=locked.center,
                status=status,
                source=source,
                enrolled_by=actor,
            )
            with transaction.atomic():
                enrollment.save()
            if enrollment.status == EnrollmentStatus.ACTIVE:
                from apps.finance.services import ensure_invoice
                ensure_invoice(enrollment)
    except IntegrityError as exc:
        raise ConflictError('The student already has an enrollment for this course.') from exc
    write_audit(
        request,
        'enrollment.create',
        f'{student.username} enrolled in {course.code} ({source}).',
        user=actor,
        center=course.center,
        entity='enrollment',
        entity_id=enrollment.id,
    )
    return enrollment


def decide_enrollment(enrollment, actor, approve, request=None):
    """Approve or reject a pending self-enrollment. Manager of that center only."""

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can decide an enrollment.')
    assert_same_center(actor, enrollment.center, request)
    assert_operational(actor)
    if enrollment.status != EnrollmentStatus.PENDING:
        raise ConflictError('This enrollment is no longer pending.')
    if approve:
        enrollment.status = EnrollmentStatus.ACTIVE
    else:
        enrollment.status = EnrollmentStatus.REJECTED
    enrollment.decided_by = actor
    enrollment.decided_at = timezone.now()
    enrollment.save()
    if enrollment.status == EnrollmentStatus.ACTIVE:
        from apps.finance.services import ensure_invoice
        ensure_invoice(enrollment)
    write_audit(
        request,
        'enrollment.decide',
        f'Enrollment {enrollment.id} {enrollment.status}.',
        user=actor,
        center=enrollment.center,
        entity='enrollment',
        entity_id=enrollment.id,
    )
    return enrollment
