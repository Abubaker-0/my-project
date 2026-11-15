"""Course serializers. Remaining capacity is calculated, never posted by the client."""

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.classes.models import ClassSchedule
from apps.common.choices import OPEN_ENROLLMENT, CourseStatus
from apps.courses.models import Course


class ScheduleReadSerializer(serializers.ModelSerializer):
    class_id = serializers.IntegerField(source='course_class_id')
    class_name = serializers.CharField(source='course_class.name')
    classroom_name = serializers.CharField(source='classroom.name')

    class Meta:
        model = ClassSchedule
        fields = ('id', 'class_id', 'class_name', 'day_of_week', 'start_time', 'end_time', 'classroom', 'classroom_name')


class ScheduleInputSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    classroom = serializers.IntegerField()


class CourseSerializer(serializers.ModelSerializer):
    """Course detail including teacher, schedules, and seats still open."""

    teacher = UserBriefSerializer(read_only=True)
    center = serializers.SerializerMethodField()
    remaining_capacity = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    schedules = serializers.SerializerMethodField()
    classes = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            'id', 'name', 'code', 'description', 'center', 'teacher', 'duration_hours',
            'start_date', 'end_date', 'fee', 'capacity', 'remaining_capacity', 'enrolled_count',
            'status', 'schedules', 'classes', 'created_at',
        )

    def get_center(self, obj):
        return {'id': obj.center_id, 'name': obj.center.name, 'code': obj.center.code}

    def _taken(self, obj):
        if hasattr(obj, 'taken_seats'):
            return obj.taken_seats
        return obj.enrollments.filter(status__in=OPEN_ENROLLMENT).count()

    def get_enrolled_count(self, obj):
        return self._taken(obj)

    def get_remaining_capacity(self, obj):
        return max(obj.capacity - self._taken(obj), 0)

    def get_schedules(self, obj):
        slots = []
        for course_class in obj.classes.all():
            if course_class.is_deleted:
                continue
            for slot in course_class.schedules.all():
                slots.append(slot)
        return ScheduleReadSerializer(slots, many=True).data

    def get_classes(self, obj):
        rows = []
        for course_class in obj.classes.all():
            if course_class.is_deleted:
                continue
            rows.append({
                'id': course_class.id,
                'name': course_class.name,
                'is_active': course_class.is_active,
                'teacher': UserBriefSerializer(course_class.teacher).data,
            })
        return rows


class CourseWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField()
    teacher = serializers.IntegerField()
    duration_hours = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    fee = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    capacity = serializers.IntegerField(min_value=1)
    section_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    schedules = ScheduleInputSerializer(many=True)

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'End date cannot be before the start date.'})
        if not attrs['schedules']:
            raise serializers.ValidationError({'schedules': 'Add at least one class schedule.'})
        if attrs['fee'] <= 0:
            raise serializers.ValidationError({'fee': 'Fee must be greater than zero.'})
        return attrs


class CourseUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180, required=False)
    description = serializers.CharField(required=False)
    teacher = serializers.IntegerField(required=False)
    duration_hours = serializers.IntegerField(min_value=1, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    fee = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    capacity = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(choices=CourseStatus.choices, required=False)
