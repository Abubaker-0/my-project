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
    roster = list(
        Enrollment.objects.filter(course_class=course_class, status=EnrollmentStatus.ACTIVE)
        .values_list('student_id', flat=True)
    )
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


def correct_attendance(record, status, actor, request=None):
    """Let the center manager correct a mark after the teacher has submitted it."""

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can edit submitted attendance.')
    session = record.session
    assert_same_center(actor, session.center, request)
    assert_operational(actor)
    if not session.is_submitted:
        raise BusinessRuleError('Attendance has not been submitted yet.')
    if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
        raise BusinessRuleError('Attendance status must be present or absent.')
    record.status = status
    record.edited_by = actor
    record.edited_at = timezone.now()
    record.save()
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
