"""Course API.

Super admin can read every center's courses and cannot create or edit them.
Teachers see courses they teach. Students see active courses in their center,
and `available=1` hides courses they have already joined.
"""

from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.classes.models import ClassSchedule, Classroom, CourseClass
from apps.common.choices import OPEN_ENROLLMENT, CourseStatus, Role
from apps.common.exceptions import BusinessRuleError
from apps.courses.models import Course
from apps.courses.serializers import CourseSerializer, CourseUpdateSerializer, CourseWriteSerializer
from apps.courses.services import create_course, set_course_status, update_course
from apps.enrollments.models import Enrollment


def _prepare(data, center_id):
    """Turn posted ids into model instances after the center check."""

    teacher = User.objects.filter(pk=data['teacher']).first()
    if teacher is None:
        raise BusinessRuleError('Teacher was not found.')
    schedules = []
    for slot in data['schedules']:
        room = Classroom.objects.filter(pk=slot['classroom'], is_deleted=False).first()
        if room is None:
            raise BusinessRuleError('Classroom was not found.')
        schedules.append({**slot, 'classroom': room})
    data = {**data, 'teacher': teacher, 'schedules': schedules}
    return data


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ('name', 'code', 'description', 'teacher__first_name', 'teacher__last_name')
    ordering_fields = ('name', 'fee', 'start_date', 'created_at')
    filterset_fields = ('status', 'center', 'teacher')

    def get_queryset(self):
        queryset = Course.objects.filter(is_deleted=False).select_related('center', 'teacher', 'teacher__profile').prefetch_related(
            Prefetch('classes', queryset=CourseClass.objects.filter(is_deleted=False).select_related('teacher', 'teacher__profile').prefetch_related(
                Prefetch('schedules', queryset=ClassSchedule.objects.select_related('classroom'))
            ))
        ).annotate(
            taken_seats=Count('enrollments', filter=Q(enrollments__status__in=list(OPEN_ENROLLMENT)), distinct=True)
        )
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            scoped = queryset
        elif user.role in (Role.CENTER_MANAGER, Role.FINANCE_MANAGER):
            scoped = queryset.filter(center_id=user.center_id)
        elif user.role == Role.TEACHER:
            scoped = queryset.filter(Q(teacher=user) | Q(classes__teacher=user)).distinct()
        elif user.role == Role.STUDENT:
            scoped = queryset.filter(center_id=user.center_id, status=CourseStatus.ACTIVE)
            if self.request.query_params.get('available') == '1':
                joined = Enrollment.objects.filter(student=user, status__in=OPEN_ENROLLMENT).values_list('course_id', flat=True)
                scoped = scoped.exclude(id__in=joined)
        else:
            scoped = queryset.none()
        return scoped

    def create(self, request, *args, **kwargs):
        serializer = CourseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _prepare(serializer.validated_data, getattr(request.user, 'center_id', None))
        course = create_course(payload, request.user, request)
        return Response(CourseSerializer(self.get_queryset().get(pk=course.pk)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        course = self.get_object()
        serializer = CourseUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if 'teacher' in data:
            teacher = get_object_or_404(User, pk=data['teacher'])
            data['teacher'] = teacher
        course = update_course(course, data, request.user, request)
        return Response(CourseSerializer(self.get_queryset().get(pk=course.pk)).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        course = set_course_status(self.get_object(), CourseStatus.ACTIVE, request.user, request)
        return Response(CourseSerializer(self.get_queryset().get(pk=course.pk)).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        course = set_course_status(self.get_object(), CourseStatus.INACTIVE, request.user, request)
        return Response(CourseSerializer(self.get_queryset().get(pk=course.pk)).data)
