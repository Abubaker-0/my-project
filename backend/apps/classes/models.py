"""Class sections, rooms, and weekly schedules for one center."""

from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class Classroom(SoftDeleteModel):
    """A physical room. Schedules cannot overlap inside the same room."""

    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='classrooms')
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['center', 'name'], name='unique_classroom_name_per_center'),
            models.CheckConstraint(check=models.Q(capacity__gte=1), name='classroom_capacity_positive'),
        ]

    def __str__(self):
        return self.name


class CourseClass(SoftDeleteModel):
    """A section of a course. Students enroll into one section.

    The model is named CourseClass because `class` is a Python keyword.
    API clients see it as a class.
    """

    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='classes')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='classes')
    name = models.CharField(max_length=120)
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='classes_teaching',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'class'
        verbose_name_plural = 'classes'
        indexes = [models.Index(fields=['center', 'teacher'])]

    def __str__(self):
        return f'{self.course.code} / {self.name}'


class ClassSchedule(TimeStampedModel):
    """One weekly meeting of a class. Times are interpreted in Asia/Kabul."""

    course_class = models.ForeignKey(CourseClass, on_delete=models.CASCADE, related_name='schedules')
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name='schedules')
    # Monday is 0, matching datetime.date.weekday().
    day_of_week = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['day_of_week', 'start_time']
        constraints = [
            models.CheckConstraint(
                check=models.Q(day_of_week__gte=0, day_of_week__lte=6),
                name='schedule_day_zero_to_six',
            ),
        ]

    def __str__(self):
        return f'{self.course_class} day {self.day_of_week} {self.start_time}'
