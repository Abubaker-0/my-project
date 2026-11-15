"""In-app notifications. Nothing here sends email, SMS, or a bank message."""

from django.utils import timezone

from apps.common.models import Notification


def notify(recipient, kind, title, body, dedupe_key=None):
    """Create one notice. A repeated dedupe key returns the original row."""

    if recipient is None:
        return None
    if dedupe_key:
        existing = Notification.objects.filter(dedupe_key=dedupe_key).first()
        if existing:
            return existing
    return Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        body=body,
        dedupe_key=dedupe_key or None,
    )


def unread_count(user):
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()


def mark_read(notification, user):
    if notification.recipient_id != user.id:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('You can only read your own notifications.')
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at', 'updated_at'])
    return notification
