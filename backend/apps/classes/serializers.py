"""Class, classroom, and schedule serializers."""

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.classes.models import ClassSchedule, Classroom, CourseClass
from apps.courses.serializers import ScheduleInputSerializer


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ('id', 'center', 'name', 'capacity', 'is_active')
        read_only_fields = ('id', 'center')


class ClassroomWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    capacity = serializers.IntegerField(min_value=1)


class ClassScheduleSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)

    class Meta:
        model = ClassSchedule
        fields = ('id', 'course_class', 'day_of_week', 'start_time', 'end_time', 'classroom', 'classroom_name')


class CourseClassSerializer(serializers.ModelSerializer):
    teacher = UserBriefSerializer(read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    schedules = ClassScheduleSerializer(many=True, read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseClass
        fields = (
            'id', 'name', 'course', 'course_name', 'center', 'teacher', 'is_active',
            'schedules', 'student_count',
        )

    def get_student_count(self, obj):
        if hasattr(obj, 'student_count'):
            return obj.student_count
        return obj.enrollments.filter(status='active').count()


class ClassWriteSerializer(serializers.Serializer):
    course = serializers.IntegerField()
    name = serializers.CharField(max_length=120)
    teacher = serializers.IntegerField()
    schedules = ScheduleInputSerializer(many=True)


class ClassUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    teacher = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)
