"""Course enrollments.

`active_key` is `{student}:{course}` while the enrollment is pending or
active, and NULL otherwise. The unique column blocks a second open enrollment
and still allows a new attempt after a rejection or withdrawal.
"""

from django.db import models

from apps.common.choices import OPEN_ENROLLMENT, EnrollmentSource, EnrollmentStatus
from apps.common.models import TimeStampedModel


class Enrollment(TimeStampedModel):
    """A student joining one class of one course inside their own center."""

    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='enrollments')
    course = models.ForeignKey('courses.Course', on_delete=models.PROTECT, related_name='enrollments')
    course_class = models.ForeignKey('classes.CourseClass', on_delete=models.PROTECT, related_name='enrollments')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='enrollments')
    status = models.CharField(max_length=20, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE)
    source = models.CharField(max_length=20, choices=EnrollmentSource.choices)
    enrolled_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrollments_made',
    )
    decided_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrollments_decided',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    active_key = models.CharField(max_length=80, null=True, blank=True, unique=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['center', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['course', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(status__in=[choice for choice, _label in EnrollmentStatus.choices]),
                name='enrollment_status_known',
            ),
            models.CheckConstraint(
                check=models.Q(source__in=[EnrollmentSource.SELF, EnrollmentSource.MANUAL]),
                name='enrollment_source_known',
            ),
        ]

    def __str__(self):
        return f'{self.student} → {self.course} ({self.status})'

    def save(self, *args, **kwargs):
        if self.status in OPEN_ENROLLMENT and self.student_id and self.course_id:
            self.active_key = f'{self.student_id}:{self.course_id}'
        else:
            self.active_key = None
        super().save(*args, **kwargs)


class WaitlistEntry(TimeStampedModel):
    """A seat request that does not reserve capacity and does not create an invoice."""

    WAITING = 'waiting'
    PROMOTED = 'promoted'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (WAITING, 'Waiting'),
        (PROMOTED, 'Promoted'),
        (CANCELLED, 'Cancelled'),
    ]

    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='waitlist_entries')
    course = models.ForeignKey('courses.Course', on_delete=models.PROTECT, related_name='waitlist_entries')
    course_class = models.ForeignKey('classes.CourseClass', on_delete=models.PROTECT, related_name='waitlist_entries')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='waitlist_entries')
    position = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=WAITING)

    class Meta:
        ordering = ['position', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                condition=models.Q(status='waiting'),
                name='one_waiting_entry_per_course',
            ),
        ]


class WithdrawalRequest(TimeStampedModel):
    """A student request to leave a course. Approval does not refund or cancel the invoice."""

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name='withdrawal_requests')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    decided_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='withdrawals_decided',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment'],
                condition=models.Q(status='pending'),
                name='one_pending_withdrawal',
            ),
        ]
