"""Submitted attendance sessions and one row per student.

Teachers create a session once. After that only the center manager can change
a row, and the status can only be present or absent.
"""

from django.db import models

from apps.common.choices import AttendanceStatus
from apps.common.models import TimeStampedModel


class Attendance(TimeStampedModel):
    """One submitted register for a class on a date."""

    course_class = models.ForeignKey('classes.CourseClass', on_delete=models.PROTECT, related_name='sessions')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='attendance_sessions')
    date = models.DateField(db_index=True)
    submitted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='attendance_submitted',
    )
    submitted_at = models.DateTimeField()
    is_submitted = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['course_class', 'date'], name='one_attendance_per_class_date'),
        ]

    def __str__(self):
        return f'{self.course_class} on {self.date}'


class AttendanceRecord(TimeStampedModel):
    """Present or absent mark for one student inside a submitted session."""

    session = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    edited_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attendance_edits',
    )
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session', 'student'], name='one_mark_per_student_session'),
            models.CheckConstraint(
                check=models.Q(status__in=[AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]),
                name='attendance_present_or_absent',
            ),
        ]

    def __str__(self):
        return f'{self.student} {self.status}'
