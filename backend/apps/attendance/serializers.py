"""Attendance serializers. Status is limited to present and absent."""

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.attendance.models import Attendance, AttendanceRecord
from apps.common.choices import AttendanceStatus


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student = UserBriefSerializer(read_only=True)
    class_name = serializers.CharField(source='session.course_class.name', read_only=True)
    course_name = serializers.CharField(source='session.course_class.course.name', read_only=True)
    date = serializers.DateField(source='session.date', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ('id', 'student', 'status', 'date', 'class_name', 'course_name', 'edited_by', 'edited_at')


class AttendanceSerializer(serializers.ModelSerializer):
    records = AttendanceRecordSerializer(many=True, read_only=True)
    class_name = serializers.CharField(source='course_class.name', read_only=True)

    class Meta:
        model = Attendance
        fields = ('id', 'course_class', 'class_name', 'center', 'date', 'submitted_by', 'submitted_at', 'is_submitted', 'records')


class MarkItemSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceStatus.choices)


class MarkAttendanceSerializer(serializers.Serializer):
    class_id = serializers.IntegerField()
    date = serializers.DateField()
    records = MarkItemSerializer(many=True)


class CorrectAttendanceSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AttendanceStatus.choices)
