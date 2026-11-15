"""Official financial reports prepared by finance and sent upward.

The snapshot is stored with the report so later payments do not rewrite a
report that was already sent to the super admin.
"""

from django.db import models

from apps.common.choices import ReportStatus
from apps.common.models import TimeStampedModel


class FinancialReport(TimeStampedModel):
    """A period report for one center."""

    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='financial_reports')
    title = models.CharField(max_length=180)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=32, choices=ReportStatus.choices, default=ReportStatus.DRAFT)
    prepared_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='reports_prepared',
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports_sent',
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    previous = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='revisions',
    )
    return_note = models.TextField(blank=True)
    returned_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports_returned',
    )
    returned_at = models.DateTimeField(null=True, blank=True)
    snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ['-period_end', '-created_at']
        indexes = [models.Index(fields=['center', 'status'])]

    def __str__(self):
        return self.title
