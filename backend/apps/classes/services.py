"""Schedule conflict checks and class maintenance.

A new slot is rejected when the teacher, the classroom, or a student already
in the class is busy. Overlap uses a half-open comparison, so a class that
ends at 10:00 may be followed by one that starts at 10:00.
"""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.services import assert_operational
from apps.classes.models import ClassSchedule, Classroom, CourseClass
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import OPEN_ENROLLMENT, ContractStatus, Role
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.enrollments.models import Enrollment


def times_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def dates_overlap(start_a, end_a, start_b, end_b):
    return start_a <= end_b and end_a >= start_b


def _require_manager(actor, center, request):
    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only a center manager can manage classes.')
    assert_same_center(actor, center, request)
    assert_operational(actor)


def assert_teacher_ready(teacher, center):
    """A class teacher must be an active teacher contracted to this center."""

    from apps.accounts.models import Contract
    from apps.accounts.services import refresh_expired_contracts

    if teacher.role != Role.TEACHER or not teacher.is_active:
        raise BusinessRuleError('Assign an active teacher from your center.')
    if teacher.center_id != center.id:
        raise BusinessRuleError('The teacher belongs to another center.')
    refresh_expired_contracts(teacher)
    if not Contract.objects.filter(user=teacher, center=center, status=ContractStatus.ACTIVE).exists():
        raise BusinessRuleError('The teacher does not have an active contract at this center.')


def assert_batch_slots(slots):
    """Reject overlapping slots inside the same create request."""

    for index, left in enumerate(slots):
        if left['start_time'] >= left['end_time']:
            raise BusinessRuleError('End time must be after start time.')
        for right in slots[index + 1:]:
            if left['day_of_week'] != right['day_of_week']:
                continue
            if not times_overlap(left['start_time'], left['end_time'], right['start_time'], right['end_time']):
                continue
            if left['classroom'].id == right['classroom'].id:
                raise ConflictError('Two schedules in this class use the same classroom at the same time.')
            raise ConflictError('Two schedules in this class overlap.')


def assert_slot_available(*, course, teacher, classroom, day, start, end, exclude_schedule_id=None, course_class=None):
    """Reject a slot that collides with a teacher, a room, or an enrolled student."""

    if start >= end:
        raise BusinessRuleError('End time must be after start time.')
    if classroom.center_id != course.center_id or classroom.is_deleted or not classroom.is_active:
        raise BusinessRuleError('Choose an active classroom from this center.')
    queryset = ClassSchedule.objects.filter(
        day_of_week=day,
        start_time__lt=end,
        end_time__gt=start,
        course_class__is_deleted=False,
        course_class__course__is_deleted=False,
        course_class__course__start_date__lte=course.end_date,
        course_class__course__end_date__gte=course.start_date,
    )
    if exclude_schedule_id:
        queryset = queryset.exclude(pk=exclude_schedule_id)
    if queryset.filter(course_class__teacher_id=teacher.id).exists():
        raise ConflictError('This teacher already has a class at that time.')
    if queryset.filter(classroom_id=classroom.id).exists():
        raise ConflictError('This classroom is already booked at that time.')
    if course_class is not None and course_class.pk:
        student_ids = Enrollment.objects.filter(
            course_class=course_class,
            status__in=OPEN_ENROLLMENT,
        ).values_list('student_id', flat=True)
        other_classes = Enrollment.objects.filter(
            student_id__in=student_ids,
            status__in=OPEN_ENROLLMENT,
        ).exclude(course_class=course_class).values_list('course_class_id', flat=True)
        if student_ids and queryset.filter(course_class_id__in=other_classes).exists():
            raise ConflictError('A student in this class already has another class at that time.')


def assert_student_free(student, course_class):
    """Block enrollment when the student already meets at one of these times."""

    new_slots = list(course_class.schedules.select_related('classroom'))
    if not new_slots:
        raise BusinessRuleError('This class does not have a schedule yet.')
    current = (
        Enrollment.objects.filter(student=student, status__in=OPEN_ENROLLMENT)
        .exclude(course_class=course_class)
        .select_related('course', 'course_class')
    )
    for enrollment in current:
        if not dates_overlap(
            enrollment.course.start_date,
            enrollment.course.end_date,
            course_class.course.start_date,
            course_class.course.end_date,
        ):
            continue
        for slot in enrollment.course_class.schedules.all():
            for new_slot in new_slots:
                if slot.day_of_week == new_slot.day_of_week and times_overlap(
                    slot.start_time, slot.end_time, new_slot.start_time, new_slot.end_time
                ):
                    raise ConflictError('The student already has a class at this time.')


def _store_schedules(course_class, slots):
    assert_batch_slots(slots)
    created = []
    for slot in slots:
        assert_slot_available(
            course=course_class.course,
            teacher=course_class.teacher,
            classroom=slot['classroom'],
            day=slot['day_of_week'],
            start=slot['start_time'],
            end=slot['end_time'],
            course_class=course_class,
        )
        created.append(ClassSchedule.objects.create(
            course_class=course_class,
            classroom=slot['classroom'],
            day_of_week=slot['day_of_week'],
            start_time=slot['start_time'],
            end_time=slot['end_time'],
        ))
    return created


def create_class(*, course, name, teacher, schedules, actor, request=None):
    """Create a section with at least one schedule. Only the center manager may do this."""

    _require_manager(actor, course.center, request)
    if course.is_deleted or course.center.is_deleted:
        raise BusinessRuleError('This course is not available.')
    if not schedules:
        raise BusinessRuleError('A class must have at least one schedule.')
    assert_teacher_ready(teacher, course.center)
    with transaction.atomic():
        course_class = CourseClass.objects.create(
            course=course,
            center=course.center,
            name=name.strip(),
            teacher=teacher,
        )
        _store_schedules(course_class, schedules)
    write_audit(request, 'class.create', f'Created class {course_class}.', user=actor, center=course.center, entity='class', entity_id=course_class.id)
    return course_class


def update_class(course_class, data, actor, request=None):
    """Rename a class or move it to another teacher in the same center."""

    _require_manager(actor, course_class.center, request)
    if 'name' in data:
        course_class.name = data['name'].strip()
    if 'is_active' in data:
        course_class.is_active = data['is_active']
    if 'teacher' in data and data['teacher'].id != course_class.teacher_id:
        assert_teacher_ready(data['teacher'], course_class.center)
        # Validate against the new teacher before the row is saved.
        for slot in course_class.schedules.select_related('classroom'):
            assert_slot_available(
                course=course_class.course,
                teacher=data['teacher'],
                classroom=slot.classroom,
                day=slot.day_of_week,
                start=slot.start_time,
                end=slot.end_time,
                exclude_schedule_id=slot.id,
                course_class=course_class,
            )
        course_class.teacher = data['teacher']
    course_class.save()
    return course_class


def add_schedule(course_class, slot, actor, request=None):
    """Append one meeting time after the conflict checks pass."""

    _require_manager(actor, course_class.center, request)
    if course_class.is_deleted:
        raise BusinessRuleError('This class is archived.')
    with transaction.atomic():
        created = _store_schedules(course_class, [slot])
    return created[0]


def delete_schedule(schedule, actor, request=None):
    """Remove a meeting time. The class must keep at least one."""

    _require_manager(actor, schedule.course_class.center, request)
    if schedule.course_class.schedules.count() <= 1:
        raise BusinessRuleError('A class must keep at least one schedule.')
    schedule.delete()


def create_classroom(center, name, capacity, actor, request=None):
    """Add a room. Names are unique inside the center."""

    _require_manager(actor, center, request)
    if capacity < 1:
        raise BusinessRuleError('Classroom capacity must be at least 1.')
    if Classroom.objects.filter(center=center, name=name.strip(), is_deleted=False).exists():
        raise ConflictError('A classroom with this name already exists.')
    room = Classroom.objects.create(center=center, name=name.strip(), capacity=capacity)
    write_audit(request, 'classroom.create', f'Created classroom {room.name}.', user=actor, center=center, entity='classroom', entity_id=room.id)
    return room


def archive_classroom(room, actor, request=None):
    """Archive a room that is not used by a current schedule."""

    _require_manager(actor, room.center, request)
    if room.schedules.filter(course_class__is_deleted=False).exists():
        raise BusinessRuleError('Remove this classroom from class schedules before archiving it.')
    room.archive()
    return room
