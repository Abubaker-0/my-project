"""Courses offered by one center.

Remaining capacity is not stored. It is the capacity minus pending and active
enrollments, calculated inside the enrollment transaction so it cannot go
negative.
"""

from django.db import models

from apps.common.choices import CourseStatus
from apps.common.models import SoftDeleteModel


class Course(SoftDeleteModel):
    """A course belongs to one center and one lead teacher from that center."""

    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='courses')
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=20)
    description = models.TextField()
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='courses_teaching',
    )
    duration_hours = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    fee = models.DecimalField(max_digits=12, decimal_places=2)
    capacity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.ACTIVE,
        db_index=True,
    )
    created_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='courses_created',
    )

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['center', 'code'], name='unique_course_code_per_center'),
            models.CheckConstraint(check=models.Q(fee__gt=0), name='course_fee_positive'),
            models.CheckConstraint(check=models.Q(capacity__gte=1), name='course_capacity_positive'),
            models.CheckConstraint(check=models.Q(duration_hours__gte=1), name='course_duration_positive'),
            models.CheckConstraint(
                check=models.Q(status__in=[choice for choice, _label in CourseStatus.choices]),
                name='course_status_known',
            ),
        ]
        indexes = [models.Index(fields=['center', 'status'])]

    def __str__(self):
        return f'{self.code} {self.name}'
