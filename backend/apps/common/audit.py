"""Write the audit log and the security logger.

Services call `write_audit` after a successful sensitive change and
`audit_denied` before raising PermissionDenied for a cross-center attempt.
"""

import logging

logger = logging.getLogger('security')


def client_ip(request):
    """Return the direct client address. Forwarded headers are not trusted."""

    if request is None:
        return None
    return request.META.get('REMOTE_ADDR')


def write_audit(request, action, message, *, user=None, center=None, entity='', entity_id='', level='info'):
    """Persist one audit row. Failures here must not hide the original error."""

    from apps.common.models import AuditLog

    actor = user
    if actor is None and request is not None and getattr(request.user, 'is_authenticated', False):
        actor = request.user
    center_obj = center if getattr(center, 'pk', None) else None
    AuditLog.objects.create(
        user=actor if getattr(actor, 'pk', None) else None,
        center=center_obj,
        action=action,
        entity=entity or '',
        entity_id=str(entity_id or ''),
        message=message,
        ip_address=client_ip(request),
        level=level,
    )
    if level == AuditLog.Level.SECURITY:
        logger.warning('%s %s', action, message)
