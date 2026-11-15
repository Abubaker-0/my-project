"""Class, classroom, and schedule API. Only a center manager can change them."""

from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.serializers import UserBriefSerializer
from apps.classes.models import ClassSchedule, Classroom, CourseClass
from apps.classes.serializers import (
    ClassScheduleSerializer,
    ClassUpdateSerializer,
    ClassWriteSerializer,
    ClassroomSerializer,
    ClassroomWriteSerializer,
    CourseClassSerializer,
)
from apps.classes.services import add_schedule, archive_classroom, create_class, create_classroom, delete_schedule, update_class
from apps.common.choices import EnrollmentStatus, Role
from apps.common.exceptions import BusinessRuleError
from apps.courses.models import Course
from apps.courses.serializers import ScheduleInputSerializer
from apps.enrollments.models import Enrollment


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    search_fields = ('name',)
    filterset_fields = ('center', 'is_active')

    def get_queryset(self):
        queryset = Classroom.objects.filter(is_deleted=False)
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.center_id:
            return queryset.filter(center_id=user.center_id)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = ClassroomWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.role != Role.CENTER_MANAGER or not request.user.center_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only a center manager can create classrooms.')
        room = create_classroom(
            request.user.center,
            serializer.validated_data['name'],
            serializer.validated_data['capacity'],
            request.user,
            request,
        )
        return Response(ClassroomSerializer(room).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        room = archive_classroom(self.get_object(), request.user, request)
        return Response(ClassroomSerializer(room).data)


class ClassViewSet(viewsets.ModelViewSet):
    serializer_class = CourseClassSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ('name', 'course__name', 'teacher__first_name', 'teacher__last_name')
    ordering_fields = ('name', 'created_at')
    filterset_fields = ('course', 'teacher', 'center', 'is_active')

    def get_queryset(self):
        queryset = CourseClass.objects.filter(is_deleted=False).select_related(
            'course', 'center', 'teacher', 'teacher__profile'
        ).prefetch_related('schedules__classroom').annotate(
            student_count=Count('enrollments', filter=Q(enrollments__status=EnrollmentStatus.ACTIVE), distinct=True)
        )
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role == Role.CENTER_MANAGER:
            return queryset.filter(center_id=user.center_id)
        if user.role == Role.TEACHER:
            return queryset.filter(teacher=user)
        if user.role == Role.STUDENT:
            # Students see the sections they joined, not every class in the center.
            return queryset.filter(
                enrollments__student=user,
                enrollments__status=EnrollmentStatus.ACTIVE,
            ).distinct()
        if user.role == Role.FINANCE_MANAGER:
            return queryset.filter(center_id=user.center_id)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = ClassWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        course = Course.objects.filter(pk=data['course'], is_deleted=False).first()
        teacher = User.objects.filter(pk=data['teacher']).first()
        if course is None or teacher is None:
            raise BusinessRuleError('Course and teacher are required.')
        schedules = []
        for slot in data['schedules']:
            room = Classroom.objects.filter(pk=slot['classroom'], is_deleted=False).first()
            if room is None:
                raise BusinessRuleError('Classroom was not found.')
            schedules.append({**slot, 'classroom': room})
        course_class = create_class(
            course=course,
            name=data['name'],
            teacher=teacher,
            schedules=schedules,
            actor=request.user,
            request=request,
        )
        return Response(CourseClassSerializer(self.get_queryset().get(pk=course_class.pk)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        serializer = ClassUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if 'teacher' in data:
            data['teacher'] = User.objects.filter(pk=data['teacher']).first()
            if data['teacher'] is None:
                raise BusinessRuleError('Teacher was not found.')
        course_class = update_class(self.get_object(), data, request.user, request)
        return Response(CourseClassSerializer(self.get_queryset().get(pk=course_class.pk)).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        if request.user.role in (Role.STUDENT, Role.FINANCE_MANAGER):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You cannot read this class roster.')
        course_class = self.get_object()
        enrollments = Enrollment.objects.filter(course_class=course_class, status=EnrollmentStatus.ACTIVE).select_related('student', 'student__profile')
        return Response(UserBriefSerializer(
            [row.student for row in enrollments],
            many=True,
            context={'request': request},
        ).data)

    @action(detail=True, methods=['post'])
    def schedules(self, request, pk=None):
        course_class = self.get_object()
        serializer = ScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot = serializer.validated_data
        room = Classroom.objects.filter(pk=slot['classroom'], is_deleted=False).first()
        if room is None:
            raise BusinessRuleError('Classroom was not found.')
        created = add_schedule(course_class, {**slot, 'classroom': room}, request.user, request)
        return Response(ClassScheduleSerializer(created).data, status=status.HTTP_201_CREATED)


class ScheduleViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Delete a single meeting time. Listing lives on the class."""

    queryset = ClassSchedule.objects.select_related('course_class', 'classroom')
    serializer_class = ClassScheduleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.center_id:
            return queryset.filter(course_class__center_id=user.center_id)
        return queryset.none()

    def destroy(self, request, pk=None):
        delete_schedule(self.get_object(), request.user, request)
        return Response({'detail': 'Schedule removed.'})
