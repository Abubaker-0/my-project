"""Enrollment API: self-enrollment, manual enrollment, and approval."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.classes.models import CourseClass
from apps.common.choices import EnrollmentSource, Role
from apps.common.exceptions import BusinessRuleError
from apps.courses.models import Course
from apps.enrollments.models import Enrollment
from apps.enrollments.serializers import EnrollmentSerializer, ManualEnrollSerializer, SelfEnrollSerializer
from apps.enrollments.services import decide_enrollment, enroll


class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    search_fields = ('student__first_name', 'student__last_name', 'student__username', 'course__name', 'course__code')
    ordering_fields = ('created_at', 'status')
    filterset_fields = ('status', 'source', 'course', 'course_class', 'student', 'center')

    def get_queryset(self):
        queryset = Enrollment.objects.select_related(
            'student', 'student__profile', 'course', 'course_class', 'center'
        )
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            scoped = queryset
        elif user.role == Role.CENTER_MANAGER:
            scoped = queryset.filter(center_id=user.center_id)
        elif user.role == Role.FINANCE_MANAGER:
            scoped = queryset.filter(center_id=user.center_id)
        elif user.role == Role.TEACHER:
            scoped = queryset.filter(course_class__teacher=user)
        elif user.role == Role.STUDENT:
            scoped = queryset.filter(student=user)
        else:
            scoped = queryset.none()
        if self.request.query_params.get('mine') == '1' and user.role == Role.STUDENT:
            return scoped
        return scoped

    @action(detail=False, methods=['post'], url_path='self-enroll')
    def self_enroll(self, request):
        serializer = SelfEnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = Course.objects.filter(pk=serializer.validated_data['course_id'], is_deleted=False).select_related('center').first()
        course_class = CourseClass.objects.filter(pk=serializer.validated_data['class_id'], is_deleted=False).select_related('course').first()
        if course is None or course_class is None:
            raise BusinessRuleError('Course or class was not found.')
        enrollment = enroll(
            student=request.user,
            course=course,
            course_class=course_class,
            actor=request.user,
            source=EnrollmentSource.SELF,
            request=request,
        )
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='manual')
    def manual(self, request):
        serializer = ManualEnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = User.objects.filter(pk=serializer.validated_data['student_id']).first()
        course = Course.objects.filter(pk=serializer.validated_data['course_id'], is_deleted=False).select_related('center').first()
        course_class = CourseClass.objects.filter(pk=serializer.validated_data['class_id'], is_deleted=False).first()
        if student is None or course is None or course_class is None:
            raise BusinessRuleError('Student, course, and class are required.')
        enrollment = enroll(
            student=student,
            course=course,
            course_class=course_class,
            actor=request.user,
            source=EnrollmentSource.MANUAL,
            request=request,
        )
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        enrollment = decide_enrollment(self.get_object(), request.user, True, request)
        return Response(EnrollmentSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        enrollment = decide_enrollment(self.get_object(), request.user, False, request)
        return Response(EnrollmentSerializer(enrollment).data)
