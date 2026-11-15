"""Shared record bases and the security audit log."""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Created and updated timestamps for reporting and support."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    """Archive a row without erasing history that reports still need.

    Lists filter `is_deleted=False`. Call `archive()` rather than `delete()`.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def archive(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])


class AuditLog(TimeStampedModel):
    """Durable record of security denials and important business actions."""

    class Level(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        SECURITY = 'security', 'Security'

    user = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    center = models.ForeignKey(
        'centers.Center',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=80, db_index=True)
    entity = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['center', 'action']),
            models.Index(fields=['level', 'created_at']),
        ]

    def __str__(self):
        return f'{self.action}: {self.message[:80]}'
