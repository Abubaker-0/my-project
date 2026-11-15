"""Attendance submission and manager corrections.

The teacher of the class submits present or absent for every active student
on a date the class actually meets. The register is then closed. Later changes
are a center-manager correction and are stamped with the editor.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.services import assert_operational
from apps.attendance.models import Attendance, AttendanceRecord
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import AttendanceStatus, EnrollmentStatus, Role
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.enrollments.models import Enrollment


def eligible_roster(course_class, day):
    """Students who held an active seat on `day`, not merely whoever is active now."""

    from datetime import datetime, time, timedelta

    # Compare instants in Python so MySQL does not need loaded timezone tables.
    next_day = timezone.make_aware(datetime.combine(day + timedelta(days=1), time.min))
    rows = []
    enrollments = Enrollment.objects.filter(
        course_class=course_class,
        created_at__lt=next_day,
    ).exclude(status__in=(EnrollmentStatus.REJECTED, EnrollmentStatus.PENDING))
    for enrollment in enrollments:
        if enrollment.status == EnrollmentStatus.ACTIVE:
            rows.append(enrollment)
        elif enrollment.status in (EnrollmentStatus.WITHDRAWN, EnrollmentStatus.COMPLETED):
            if enrollment.decided_at and timezone.localtime(enrollment.decided_at).date() > day:
                rows.append(enrollment)
    return rows


def mark_attendance(*, course_class, day, records, actor, request=None):
    """Submit the full register for one class date. Partial registers are refused."""

    if actor.role != Role.TEACHER:
        raise PermissionDenied('Only the assigned teacher can mark attendance.')
    assert_operational(actor)
    if course_class.teacher_id != actor.id:
        raise PermissionDenied('Teachers can mark attendance only for their own classes.')
    assert_same_center(actor, course_class.center, request)
    today = timezone.localdate()
    if day > today:
        raise BusinessRuleError('Attendance cannot be marked for a future date.')
    course = course_class.course
    if day < course.start_date or day > course.end_date:
        raise BusinessRuleError('The date is outside the course period.')
    if not course_class.schedules.filter(day_of_week=day.weekday()).exists():
        raise BusinessRuleError('This class does not meet on the selected date.')
    if Attendance.objects.filter(course_class=course_class, date=day).exists():
        raise ConflictError('Attendance was already submitted. The center manager can correct it.')
    roster = [enrollment.student_id for enrollment in eligible_roster(course_class, day)]
    if not roster:
        raise BusinessRuleError('This class has no active students to mark.')
    incoming = {}
    for item in records:
        student_id = item['student_id']
        status = item['status']
        if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
            raise BusinessRuleError('Attendance status must be present or absent.')
        if student_id in incoming:
            raise BusinessRuleError('Each student can be marked only once.')
        incoming[student_id] = status
    if set(incoming) != set(roster):
        raise BusinessRuleError('Attendance must include every active student exactly once.')
    with transaction.atomic():
        session = Attendance.objects.create(
            course_class=course_class,
            center=course_class.center,
            date=day,
            submitted_by=actor,
            submitted_at=timezone.now(),
            is_submitted=True,
        )
        AttendanceRecord.objects.bulk_create([
            AttendanceRecord(session=session, student_id=student_id, status=status)
            for student_id, status in incoming.items()
        ])
    write_audit(
        request,
        'attendance.mark',
        f'Attendance submitted for class {course_class.id} on {day}.',
        user=actor,
        center=course_class.center,
        entity='attendance',
        entity_id=session.id,
    )
    return session


def correct_attendance(record, status, actor, reason, request=None):
    """Let the center manager correct a mark and keep the previous value."""

    from apps.attendance.models import AttendanceCorrection

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can edit submitted attendance.')
    session = record.session
    assert_same_center(actor, session.center, request)
    assert_operational(actor)
    if not session.is_submitted:
        raise BusinessRuleError('Attendance has not been submitted yet.')
    if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
        raise BusinessRuleError('Attendance status must be present or absent.')
    reason = (reason or '').strip()
    if len(reason) < 5:
        raise BusinessRuleError('A correction needs a reason of at least 5 characters.')
    if record.status == status:
        raise BusinessRuleError('The mark is already set to that status.')
    old_status = record.status
    record.status = status
    record.edited_by = actor
    record.edited_at = timezone.now()
    record.save()
    AttendanceCorrection.objects.create(
        record=record,
        old_status=old_status,
        new_status=status,
        reason=reason,
        actor=actor,
    )
    write_audit(
        request,
        'attendance.correct',
        f'Corrected attendance record {record.id} to {status}.',
        user=actor,
        center=session.center,
        entity='attendance_record',
        entity_id=record.id,
    )
    return record


def request_correction(record, status, actor, reason, request=None):
    """Teacher asks for a correction. The stored mark does not change yet."""

    from apps.attendance.models import AttendanceCorrectionRequest
    from apps.common.permissions_catalog import has_permission

    session = record.session
    if actor.role != Role.TEACHER or session.course_class.teacher_id != actor.id:
        raise PermissionDenied('Only the teacher of this class can request a correction.')
    if not has_permission(actor, 'attendance.request_correction', session.center):
        raise PermissionDenied('Correction requests are restricted for this center.')
    assert_same_center(actor, session.center, request)
    assert_operational(actor)
    if not session.is_submitted:
        raise BusinessRuleError('Attendance has not been submitted yet.')
    if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
        raise BusinessRuleError('Attendance status must be present or absent.')
    reason = (reason or '').strip()
    if len(reason) < 5:
        raise BusinessRuleError('A correction request needs a reason of at least 5 characters.')
    if record.status == status:
        raise BusinessRuleError('The mark is already set to that status.')
    if AttendanceCorrectionRequest.objects.filter(record=record, status=AttendanceCorrectionRequest.PENDING).exists():
        raise ConflictError('A correction request is already waiting for this mark.')
    row = AttendanceCorrectionRequest.objects.create(
        record=record,
        requested_status=status,
        reason=reason,
        requested_by=actor,
    )
    from apps.common.notifications import notify
    notify(
        session.center.get_active_manager(),
        'attendance',
        'Attendance correction requested',
        f'{actor.username} asked to change a mark to {status}.',
        dedupe_key=f'attendance-correction:{row.id}',
    )
    write_audit(
        request,
        'attendance.correction_request',
        f'Correction requested for record {record.id}.',
        user=actor,
        center=session.center,
        entity='attendance_record',
        entity_id=record.id,
    )
    return row


def decide_correction(row, actor, approve, note='', request=None):
    """Manager approval applies the requested mark. Rejection leaves it unchanged."""

    from apps.attendance.models import AttendanceCorrectionRequest

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can decide a correction request.')
    assert_same_center(actor, row.record.session.center, request)
    assert_operational(actor)
    if row.status != AttendanceCorrectionRequest.PENDING:
        raise ConflictError('This correction request has already been decided.')
    if approve:
        correct_attendance(row.record, row.requested_status, actor, row.reason, request)
        row.status = AttendanceCorrectionRequest.APPROVED
    else:
        row.status = AttendanceCorrectionRequest.REJECTED
    row.decided_by = actor
    row.decision_note = (note or '').strip()
    row.save()
    return row
