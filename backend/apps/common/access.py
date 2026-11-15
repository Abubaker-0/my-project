"""Role and center checks used by every write service.

Object queries are also filtered by center in the viewsets. These helpers
cover ids that arrive in the request body, which queryset filtering cannot see.
"""

from rest_framework.exceptions import PermissionDenied

from apps.common.audit import write_audit
from apps.common.choices import Role
from apps.common.models import AuditLog


def require_roles(user, roles, message='You do not have permission to perform this action.'):
    """Reject the request when the authenticated role is not in `roles`."""

    if user.role not in roles:
        raise PermissionDenied(message)


def assert_same_center(user, center, request=None):
    """Block access to a center the user does not belong to.

    Super admins may read every center. Operational services reject them
    before calling this helper. A mismatch is stored as a security audit row
    so IDOR attempts are visible to the super admin.
    """

    center_id = getattr(center, 'id', center)
    if user.role == Role.SUPER_ADMIN:
        return center_id
    if not center_id or user.center_id != center_id:
        write_audit(
            request,
            'security.cross_center',
            f'{user.username} attempted to access center {center_id}.',
            user=user,
            entity='center',
            entity_id=center_id,
            level=AuditLog.Level.SECURITY,
        )
        raise PermissionDenied('You cannot access another center.')
    return center_id
