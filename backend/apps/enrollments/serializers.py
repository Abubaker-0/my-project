"""Enrollment serializers."""

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.enrollments.models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserBriefSerializer(read_only=True)
    course = serializers.SerializerMethodField()
    course_class = serializers.SerializerMethodField()
    center = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            'id', 'student', 'course', 'course_class', 'center', 'status', 'source',
            'enrolled_by', 'decided_at', 'notes', 'created_at',
        )

    def get_course(self, obj):
        return {
            'id': obj.course_id,
            'name': obj.course.name,
            'code': obj.course.code,
            'fee': str(obj.course.fee),
            'status': obj.course.status,
            'start_date': obj.course.start_date,
            'end_date': obj.course.end_date,
        }

    def get_course_class(self, obj):
        return {'id': obj.course_class_id, 'name': obj.course_class.name}

    def get_center(self, obj):
        return {'id': obj.center_id, 'name': obj.center.name, 'code': obj.center.code}


class SelfEnrollSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    class_id = serializers.IntegerField()


class ManualEnrollSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    class_id = serializers.IntegerField()
