"""Attendance API for teachers, managers, and students."""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserBriefSerializer
from apps.attendance.models import Attendance, AttendanceRecord
from apps.attendance.serializers import (
    AttendanceRecordSerializer,
    AttendanceSerializer,
    CorrectAttendanceSerializer,
    MarkAttendanceSerializer,
)
from apps.attendance.services import correct_attendance, mark_attendance
from apps.classes.models import CourseClass
from apps.common.choices import EnrollmentStatus, Role
from apps.common.exceptions import BusinessRuleError
from apps.enrollments.models import Enrollment


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceSerializer
    filterset_fields = ('course_class', 'date', 'center')
    ordering_fields = ('date',)

    def get_queryset(self):
        queryset = Attendance.objects.select_related('course_class', 'course_class__course', 'submitted_by').prefetch_related(
            'records__student__profile'
        )
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role == Role.CENTER_MANAGER:
            return queryset.filter(center_id=user.center_id)
        if user.role == Role.TEACHER:
            return queryset.filter(course_class__teacher=user)
        if user.role == Role.STUDENT:
            return queryset.filter(records__student=user).distinct()
        return queryset.none()

    @action(detail=False, methods=['get'])
    def roster(self, request):
        """Students to mark, plus any mark already stored for that date."""

        class_id = request.query_params.get('class_id')
        day = request.query_params.get('date')
        if not class_id or not day:
            raise BusinessRuleError('class_id and date are required.')
        course_class = CourseClass.objects.filter(pk=class_id, is_deleted=False).first()
        if course_class is None or not self._can_see_class(request.user, course_class):
            raise BusinessRuleError('Class was not found.')
        session = Attendance.objects.filter(course_class=course_class, date=day).first()
        existing = {}
        if session:
            existing = {record.student_id: record for record in session.records.all()}
        students = []
        enrollments = Enrollment.objects.filter(course_class=course_class, status=EnrollmentStatus.ACTIVE).select_related('student', 'student__profile')
        editable = request.user.role == Role.CENTER_MANAGER and session is not None
        for enrollment in enrollments:
            record = existing.get(enrollment.student_id)
            students.append({
                'student': UserBriefSerializer(enrollment.student).data,
                'record_id': record.id if record else None,
                'status': record.status if record else None,
                'editable': editable,
            })
        return Response({
            'class_id': course_class.id,
            'date': day,
            'submitted': session is not None,
            'students': students,
        })

    def _can_see_class(self, user, course_class):
        if user.role == Role.SUPER_ADMIN:
            return True
        if user.role == Role.CENTER_MANAGER:
            return course_class.center_id == user.center_id
        if user.role == Role.TEACHER:
            return course_class.teacher_id == user.id
        return False

    @action(detail=False, methods=['post'])
    def mark(self, request):
        serializer = MarkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_class = CourseClass.objects.filter(pk=serializer.validated_data['class_id'], is_deleted=False).select_related('course', 'center').first()
        if course_class is None:
            raise BusinessRuleError('Class was not found.')
        session = mark_attendance(
            course_class=course_class,
            day=serializer.validated_data['date'],
            records=serializer.validated_data['records'],
            actor=request.user,
            request=request,
        )
        return Response(AttendanceSerializer(self.get_queryset().get(pk=session.pk)).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my')
    def my_records(self, request):
        if request.user.role != Role.STUDENT:
            records = AttendanceRecord.objects.filter(session__course_class__teacher=request.user)
        else:
            records = AttendanceRecord.objects.filter(student=request.user)
        records = records.select_related('student', 'student__profile', 'session', 'session__course_class', 'session__course_class__course')
        page = self.paginate_queryset(records)
        serializer = AttendanceRecordSerializer(page or records, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        records = AttendanceRecord.objects.all()
        user = request.user
        if user.role == Role.STUDENT:
            records = records.filter(student=user)
        elif user.role == Role.TEACHER:
            records = records.filter(session__course_class__teacher=user)
        elif user.role == Role.SUPER_ADMIN:
            pass
        elif user.center_id:
            records = records.filter(session__center_id=user.center_id)
        else:
            records = records.none()
        present = records.filter(status='present').count()
        absent = records.filter(status='absent').count()
        total = present + absent
        return Response({'present': present, 'absent': absent, 'rate': round((present / total) * 100, 1) if total else 0})


class AttendanceRecordViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Manager correction of a submitted mark."""

    serializer_class = AttendanceRecordSerializer

    def get_queryset(self):
        queryset = AttendanceRecord.objects.select_related('session', 'student', 'student__profile')
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.center_id:
            return queryset.filter(session__center_id=user.center_id)
        return queryset.none()

    def partial_update(self, request, pk=None):
        serializer = CorrectAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = correct_attendance(self.get_object(), serializer.validated_data['status'], request.user, request)
        return Response(AttendanceRecordSerializer(record).data)
