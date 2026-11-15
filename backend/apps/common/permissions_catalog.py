"""Code-defined permission ceiling.

Overrides may only narrow a configurable permission. Protected duties stay in
the service role checks and cannot be stored as a denial.
"""

from dataclasses import dataclass

from apps.common.choices import Role


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    ceiling: frozenset
    protected: bool
    description: str


def _spec(code, roles, protected, description):
    return PermissionSpec(code, frozenset(roles), protected, description)


CATALOG = {
    spec.code: spec
    for spec in (
        _spec('centers.manage', [Role.SUPER_ADMIN], True, 'Create, activate, and archive centers.'),
        _spec('policies.manage', [Role.SUPER_ADMIN], True, 'Change organization policy.'),
        _spec('policies.center', [Role.CENTER_MANAGER], True, 'Change center policy inside the global ceiling.'),
        _spec('users.manage_managers', [Role.SUPER_ADMIN], True, 'Create and assign center managers.'),
        _spec('users.manage_staff', [Role.CENTER_MANAGER], True, 'Create finance managers, teachers, and students.'),
        _spec('courses.manage', [Role.CENTER_MANAGER], True, 'Create courses, classes, rooms, and schedules.'),
        _spec('enrollments.decide', [Role.CENTER_MANAGER], True, 'Approve, reject, complete, and decide withdrawals.'),
        _spec('attendance.mark', [Role.TEACHER], True, 'Submit present or absent for an assigned class.'),
        _spec('attendance.correct', [Role.CENTER_MANAGER], True, 'Correct a submitted mark with a reason.'),
        _spec('finance.collect', [Role.FINANCE_MANAGER], True, 'Record payments, plans, and scholarships.'),
        _spec('finance.refund_request', [Role.FINANCE_MANAGER, Role.STUDENT], True, 'Request a refund.'),
        _spec('finance.refund_decide', [Role.CENTER_MANAGER], True, 'Approve or reject a refund.'),
        _spec('reports.prepare', [Role.FINANCE_MANAGER], False, 'Draft and revise official finance reports.'),
        _spec('reports.send', [Role.CENTER_MANAGER], True, 'Send or return a submitted report.'),
        _spec('reports.read_sent', [Role.SUPER_ADMIN], True, 'Read official reports sent to head office.'),
        _spec('exports.invoices', [Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER], False, 'Export invoices in scope.'),
        _spec('waitlist.promote', [Role.CENTER_MANAGER], False, 'Promote a waitlist entry after a fresh eligibility check.'),
        _spec('integrity.read', [Role.SUPER_ADMIN], True, 'Read the data-integrity dashboard.'),
    )
}


def has_permission(user, code, center=None):
    """Return whether `user` may use `code` after global and center narrowing."""

    from apps.common.models import PermissionOverride

    spec = CATALOG.get(code)
    if spec is None or user.role not in spec.ceiling:
        return False
    if spec.protected:
        return True
    if PermissionOverride.objects.filter(role=user.role, code=code, center__isnull=True, allowed=False).exists():
        return False
    center_id = getattr(center, 'id', center)
    if center_id and PermissionOverride.objects.filter(
        role=user.role, code=code, center_id=center_id, allowed=False,
    ).exists():
        return False
    return True


def explain_permissions(user, center=None):
    """Describe the effective permission and why it is allowed or denied."""

    from apps.common.models import PermissionOverride

    rows = []
    center_id = getattr(center, 'id', center) or getattr(user, 'center_id', None)
    for spec in CATALOG.values():
        if user.role not in spec.ceiling:
            rows.append({'code': spec.code, 'allowed': False, 'source': 'outside_ceiling', 'protected': spec.protected})
            continue
        if spec.protected:
            rows.append({'code': spec.code, 'allowed': True, 'source': 'protected', 'protected': True})
            continue
        if PermissionOverride.objects.filter(role=user.role, code=spec.code, center__isnull=True, allowed=False).exists():
            rows.append({'code': spec.code, 'allowed': False, 'source': 'global_restriction', 'protected': False})
            continue
        if center_id and PermissionOverride.objects.filter(
            role=user.role, code=spec.code, center_id=center_id, allowed=False,
        ).exists():
            rows.append({'code': spec.code, 'allowed': False, 'source': 'center_restriction', 'protected': False})
            continue
        rows.append({'code': spec.code, 'allowed': True, 'source': 'default', 'protected': False})
    return rows


def set_permission_override(*, actor, role, code, allowed, center=None, request=None):
    """Store a restriction, or remove it when `allowed` restores the default."""

    from rest_framework.exceptions import PermissionDenied

    from apps.common.audit import write_audit
    from apps.common.choices import Role
    from apps.common.exceptions import BusinessRuleError
    from apps.common.models import PermissionOverride

    spec = CATALOG.get(code)
    if spec is None:
        raise BusinessRuleError('Unknown permission.')
    if spec.protected:
        raise BusinessRuleError('This separation of duties cannot be changed in settings.')
    if role not in spec.ceiling:
        raise BusinessRuleError('That role is outside the permission ceiling.')
    if actor.role == Role.SUPER_ADMIN:
        pass
    elif actor.role == Role.CENTER_MANAGER:
        if center is None or actor.center_id != getattr(center, 'id', center):
            raise PermissionDenied('A center manager can narrow permissions only for their own center.')
        if role == Role.SUPER_ADMIN:
            raise PermissionDenied('Center settings cannot change the super admin.')
    else:
        raise PermissionDenied('You cannot change permissions.')
    lookup = {'role': role, 'code': code, 'center': center}
    if allowed:
        PermissionOverride.objects.filter(**lookup).delete()
        state = 'restored'
    else:
        PermissionOverride.objects.update_or_create(**lookup, defaults={'allowed': False})
        state = 'restricted'
    write_audit(
        request,
        'permission.override',
        f'{code} for {role} {state}.',
        user=actor,
        center=center,
        entity='permission',
        entity_id=code,
    )
    return state
