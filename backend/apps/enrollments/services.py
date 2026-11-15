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

    from apps.centers.policy import resolve_policy

    policy = resolve_policy(course.center)
    if source == EnrollmentSource.SELF:
        if actor.role != Role.STUDENT or actor.id != student.id:
            raise PermissionDenied('Students can only enroll themselves.')
        assert_operational(actor)
        if not policy['self_enrollment']['effective']:
            raise BusinessRuleError('Self-enrollment is turned off. A center manager can enroll the student.')
        status = EnrollmentStatus.PENDING if policy['approval_required']['effective'] else EnrollmentStatus.ACTIVE
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
            class_taken = Enrollment.objects.filter(course_class=course_class, status__in=OPEN_ENROLLMENT).count()
            room_caps = [
                slot.classroom.capacity
                for slot in course_class.schedules.select_related('classroom')
                if slot.classroom_id and not slot.classroom.is_deleted
            ]
            if room_caps and class_taken >= min(room_caps):
                raise ConflictError('This classroom cannot take another student.')
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


def join_waitlist(*, student, course, course_class, actor, request=None):
    """Record a waitlist place. It does not hold a seat or create an invoice."""

    from apps.enrollments.models import WaitlistEntry

    from apps.centers.policy import resolve_policy

    if actor.role != Role.STUDENT or actor.id != student.id:
        raise PermissionDenied('Students can only join a waitlist for themselves.')
    assert_operational(actor)
    if not resolve_policy(course.center)['waitlist']['effective']:
        raise BusinessRuleError('The waitlist is closed.')
    if student.center_id != course.center_id or course_class.course_id != course.id:
        raise PermissionDenied('A student cannot wait for a class at another center.')
    if Enrollment.objects.filter(student=student, course=course, status__in=OPEN_ENROLLMENT).exists():
        raise ConflictError('The student already has an enrollment for this course.')
    if WaitlistEntry.objects.filter(student=student, course=course, status=WaitlistEntry.WAITING).exists():
        raise ConflictError('The student is already waiting for this course.')
    with transaction.atomic():
        Course.objects.select_for_update().get(pk=course.pk)
        last = WaitlistEntry.objects.filter(course=course).order_by('-position').first()
        entry = WaitlistEntry.objects.create(
            student=student,
            course=course,
            course_class=course_class,
            center=course.center,
            position=(last.position + 1) if last else 1,
            status=WaitlistEntry.WAITING,
        )
    write_audit(
        request,
        'waitlist.join',
        f'{student.username} joined the waitlist for {course.code}.',
        user=actor,
        center=course.center,
        entity='waitlist',
        entity_id=entry.id,
    )
    return entry


def promote_waitlist(entry, actor, request=None):
    """Manager promotion re-checks every enrollment rule before a seat is taken."""

    from apps.common.permissions_catalog import has_permission
    from apps.enrollments.models import WaitlistEntry

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can promote a waitlist entry.')
    if not has_permission(actor, 'waitlist.promote', entry.center):
        raise PermissionDenied('Waitlist promotion is restricted for this center.')
    assert_same_center(actor, entry.center, request)
    assert_operational(actor)
    with transaction.atomic():
        entry = WaitlistEntry.objects.select_for_update().get(pk=entry.pk)
        if entry.status != WaitlistEntry.WAITING:
            raise ConflictError('This waitlist entry is no longer waiting.')
        enrollment = enroll(
            student=entry.student,
            course=entry.course,
            course_class=entry.course_class,
            actor=actor,
            source=EnrollmentSource.MANUAL,
            request=request,
        )
        entry.status = WaitlistEntry.PROMOTED
        entry.save(update_fields=['status', 'updated_at'])
    return enrollment


def request_withdrawal(enrollment, actor, reason, request=None):
    """Ask to leave. The invoice and any refund stay on their own workflows."""

    from apps.common.notifications import notify
    from apps.enrollments.models import WithdrawalRequest

    if actor.role != Role.STUDENT or actor.id != enrollment.student_id:
        raise PermissionDenied('Students can request withdrawal only for their own enrollment.')
    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise BusinessRuleError('Only an active enrollment can be withdrawn.')
    if len((reason or '').strip()) < 5:
        raise BusinessRuleError('Explain the withdrawal in at least 5 characters.')
    if WithdrawalRequest.objects.filter(enrollment=enrollment, status=WithdrawalRequest.PENDING).exists():
        raise ConflictError('A withdrawal request is already waiting.')
    row = WithdrawalRequest.objects.create(enrollment=enrollment, reason=reason.strip())
    notify(
        enrollment.center.get_active_manager(),
        'withdrawal',
        'Withdrawal request',
        f'{actor.username} asked to leave {enrollment.course.code}.',
        dedupe_key=f'withdrawal:{row.id}',
    )
    write_audit(
        request,
        'enrollment.withdraw_request',
        f'Withdrawal requested for enrollment {enrollment.id}.',
        user=actor,
        center=enrollment.center,
        entity='enrollment',
        entity_id=enrollment.id,
    )
    return row


def decide_withdrawal(row, actor, approve, note='', request=None):
    """Approve or reject. Approval releases the seat and does not issue a refund."""

    from apps.enrollments.models import WithdrawalRequest

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can decide a withdrawal.')
    assert_same_center(actor, row.enrollment.center, request)
    assert_operational(actor)
    if row.status != WithdrawalRequest.PENDING:
        raise ConflictError('This withdrawal has already been decided.')
    row.status = WithdrawalRequest.APPROVED if approve else WithdrawalRequest.REJECTED
    row.decided_by = actor
    row.decided_at = timezone.now()
    row.decision_note = note or ''
    row.save()
    if approve:
        enrollment = row.enrollment
        enrollment.status = EnrollmentStatus.WITHDRAWN
        enrollment.decided_by = actor
        enrollment.decided_at = timezone.now()
        enrollment.save()
    write_audit(
        request,
        'enrollment.withdraw_decide',
        f'Withdrawal {row.id} {row.status}.',
        user=actor,
        center=row.enrollment.center,
        entity='withdrawal',
        entity_id=row.id,
    )
    return row


def complete_enrollment(enrollment, actor, request=None):
    """Close an active enrollment after the course end date. It is no longer open."""

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can complete an enrollment.')
    assert_same_center(actor, enrollment.center, request)
    assert_operational(actor)
    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise ConflictError('Only an active enrollment can be completed.')
    if enrollment.course.end_date > timezone.localdate():
        raise BusinessRuleError('Completion is available after the course end date.')
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.decided_by = actor
    enrollment.decided_at = timezone.now()
    enrollment.save()
    write_audit(
        request,
        'enrollment.complete',
        f'Enrollment {enrollment.id} completed.',
        user=actor,
        center=enrollment.center,
        entity='enrollment',
        entity_id=enrollment.id,
    )
    return enrollment
