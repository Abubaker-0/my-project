"""Course creation and updates. Super admin is intentionally refused.

A course is created together with its first class and schedule so the record
always has a teacher, a fee, a capacity, and a meeting time.
"""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.classes.services import assert_teacher_ready, create_class
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import OPEN_ENROLLMENT, CourseStatus, Role
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.courses.models import Course


def _manager(actor, center, request):
    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only a center manager can manage courses.')
    assert_same_center(actor, center, request)
    from apps.accounts.services import assert_operational
    assert_operational(actor)


def unique_course_code(center, name, requested=None):
    """Build a center-unique course code, or accept one the manager typed."""

    if requested:
        code = requested.strip().upper()
        if Course.objects.filter(center=center, code=code, is_deleted=False).exists():
            raise ConflictError('That course code is already used in this center.')
        return code
    base = ''.join(character for character in name.upper() if character.isalnum())[:8] or 'COURSE'
    code = base
    number = 1
    while Course.objects.filter(center=center, code=code).exists():
        number += 1
        code = f'{base[:6]}{number}'
    return code


def create_course(data, actor, request=None):
    """Create a course and its first scheduled section in one transaction."""

    if actor.role == Role.SUPER_ADMIN:
        raise PermissionDenied('Super admin can view courses but cannot create them.')
    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only a center manager can create courses.')
    center = actor.center
    _manager(actor, center, request)
    if data['end_date'] < data['start_date']:
        raise BusinessRuleError('The course end date cannot be before the start date.')
    if not data.get('schedules'):
        raise BusinessRuleError('Add at least one class schedule.')
    teacher = data['teacher']
    assert_teacher_ready(teacher, center)
    with transaction.atomic():
        course = Course.objects.create(
            center=center,
            name=data['name'].strip(),
            code=unique_course_code(center, data['name'], data.get('code')),
            description=data['description'].strip(),
            teacher=teacher,
            duration_hours=data['duration_hours'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            fee=data['fee'],
            capacity=data['capacity'],
            status=CourseStatus.ACTIVE,
            created_by=actor,
        )
        create_class(
            course=course,
            name=(data.get('section_name') or 'Section A').strip() or 'Section A',
            teacher=teacher,
            schedules=data['schedules'],
            actor=actor,
            request=request,
        )
    write_audit(request, 'course.create', f'Created course {course.code}.', user=actor, center=center, entity='course', entity_id=course.id)
    return course


def update_course(course, data, actor, request=None):
    """Update course details. Capacity cannot drop below current enrollments."""

    _manager(actor, course.center, request)
    if course.is_deleted:
        raise BusinessRuleError('This course is archived.')
    if 'name' in data:
        course.name = data['name'].strip()
    if 'description' in data:
        course.description = data['description'].strip()
    if 'duration_hours' in data:
        course.duration_hours = data['duration_hours']
    if 'fee' in data:
        # Existing invoices keep the fee they were issued with.
        course.fee = data['fee']
    if 'start_date' in data:
        course.start_date = data['start_date']
    if 'end_date' in data:
        course.end_date = data['end_date']
    if course.end_date < course.start_date:
        raise BusinessRuleError('The course end date cannot be before the start date.')
    if 'capacity' in data:
        taken = course.enrollments.filter(status__in=OPEN_ENROLLMENT).count()
        if data['capacity'] < taken:
            raise BusinessRuleError('Capacity cannot be lower than the current enrollments.')
        course.capacity = data['capacity']
    if 'teacher' in data:
        assert_teacher_ready(data['teacher'], course.center)
        course.teacher = data['teacher']
    if 'status' in data:
        course.status = data['status']
    if 'start_date' in data or 'end_date' in data:
        # A longer course can collide with a teacher or room that was previously free.
        from apps.classes.services import assert_slot_available
        for course_class in course.classes.filter(is_deleted=False).prefetch_related('schedules__classroom'):
            for slot in course_class.schedules.all():
                assert_slot_available(
                    course=course,
                    teacher=course_class.teacher,
                    classroom=slot.classroom,
                    day=slot.day_of_week,
                    start=slot.start_time,
                    end=slot.end_time,
                    exclude_schedule_id=slot.id,
                    course_class=course_class,
                )
    course.save()
    if 'teacher' in data:
        classes = list(course.classes.filter(is_deleted=False))
        if len(classes) == 1 and classes[0].teacher_id != course.teacher_id:
            from apps.classes.services import update_class
            update_class(classes[0], {'teacher': course.teacher}, actor, request)
    return course


def set_course_status(course, status, actor, request=None):
    """Activate, pause, or complete a course. Enrollment requires the active status."""

    _manager(actor, course.center, request)
    if status not in CourseStatus.values:
        raise BusinessRuleError('Unknown course status.')
    course.status = status
    course.save(update_fields=['status', 'updated_at'])
    write_audit(request, 'course.status', f'{course.code} is now {status}.', user=actor, center=course.center, entity='course', entity_id=course.id)
    return course
