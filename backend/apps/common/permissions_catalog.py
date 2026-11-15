"""Code-defined permission ceiling.

Overrides may only narrow a configurable permission. Protected duties stay in
the service role checks and cannot be stored as a denial. Permission checks
read the database on every call, so a change applies before the JWT expires.
"""

from dataclasses import dataclass

from apps.common.choices import Role


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    ceiling: frozenset
    protected: bool
    description: str
    scope: str
    conditions: str


def _spec(code, roles, protected, description, scope, conditions):
    return PermissionSpec(code, frozenset(roles), protected, description, scope, conditions)


CATALOG = {
    spec.code: spec
    for spec in (
        _spec('centers.manage', [Role.SUPER_ADMIN], True, 'Create, activate, and archive centers.', 'organization', 'Super admin only.'),
        _spec('policies.manage', [Role.SUPER_ADMIN], True, 'Change organization policy.', 'organization', 'Protected. Cannot be removed, so governance cannot lock the super admin out.'),
        _spec('policies.center', [Role.CENTER_MANAGER], True, 'Change center policy inside the global ceiling.', 'own center', 'Active contract and an eligible center manager.'),
        _spec('users.manage_managers', [Role.SUPER_ADMIN], True, 'Create and assign center managers.', 'organization', 'Super admin only.'),
        _spec('users.manage_staff', [Role.CENTER_MANAGER], True, 'Create finance managers, teachers, and students.', 'own center', 'Eligible manager and active center.'),
        _spec('courses.manage', [Role.CENTER_MANAGER], True, 'Create courses, classes, rooms, and schedules.', 'own center', 'Eligible manager. Super admin cannot use this.'),
        _spec('enrollments.decide', [Role.CENTER_MANAGER], True, 'Approve, reject, complete, and decide withdrawals.', 'own center', 'Eligible manager.'),
        _spec('attendance.mark', [Role.TEACHER], True, 'Submit present or absent for an assigned class.', 'assigned class', 'Active contract and a class taught by this teacher.'),
        _spec('attendance.correct', [Role.CENTER_MANAGER], True, 'Correct a submitted mark with a reason.', 'own center', 'Manager only. Teachers file a request instead.'),
        _spec('attendance.request_correction', [Role.TEACHER], False, 'Ask the manager to correct a submitted mark.', 'assigned class', 'The class must already be submitted. Approval still belongs to the manager.'),
        _spec('finance.collect', [Role.FINANCE_MANAGER], True, 'Record payments, plans, and scholarships.', 'own center', 'Active contract. Amounts and methods stay server-side.'),
        _spec('finance.refund_request', [Role.FINANCE_MANAGER, Role.STUDENT], True, 'Request a refund when policy allows it.', 'own invoice or own center', 'Policy can turn requests off. The role itself cannot be reassigned.'),
        _spec('finance.refund_decide', [Role.CENTER_MANAGER], True, 'Approve or reject a refund.', 'own center', 'Manager only. Approval records a refund and does not send a transfer.'),
        _spec('reports.prepare', [Role.FINANCE_MANAGER], False, 'Draft, submit, and revise official finance reports.', 'own center', 'Create, submit, and revise all use this code.'),
        _spec('reports.send', [Role.CENTER_MANAGER], True, 'Send or return a submitted report.', 'own center', 'Manager only. Snapshots are not edited.'),
        _spec('reports.read_sent', [Role.SUPER_ADMIN], True, 'Read official reports sent to head office.', 'sent reports', 'Drafts stay hidden unless a status filter is requested.'),
        _spec('exports.invoices', [Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER], False, 'Export invoices in scope.', 'own center, or all centers for super admin', 'A center restriction cannot exceed a global denial.'),
        _spec('waitlist.promote', [Role.CENTER_MANAGER], False, 'Promote a waitlist entry after a fresh eligibility check.', 'own center', 'Promotion rechecks capacity. It does not create a charge by itself.'),
        _spec('integrity.read', [Role.SUPER_ADMIN], True, 'Read the data-integrity dashboard.', 'organization', 'Read only. Nothing is repaired.'),
    )
}

# Routes closed when a configurable permission is denied. Protected codes are not listed.
CLOSED_ROUTES = {
    'reports.prepare': [
        'POST /api/reports/financial/',
        'POST /api/reports/financial/<id>/submit/',
        'POST /api/reports/financial/<id>/revise/',
    ],
    'exports.invoices': ['GET /api/reports/export/invoices/'],
    'waitlist.promote': ['POST /api/enrollments/promote-waitlist/'],
    'attendance.request_correction': ['POST /api/attendance/correction-requests/'],
}

LOCKOUT_NOTE = (
    'Protected governance access stays with the super admin role and is not stored as a grant. '
    'A settings change cannot remove it.'
)


def role_has_permission(role, code, center=None):
    """Effective permission for a role, after global and center narrowing."""

    from apps.common.models import PermissionOverride

    spec = CATALOG.get(code)
    if spec is None or role not in spec.ceiling:
        return False
    if spec.protected:
        return True
    if PermissionOverride.objects.filter(role=role, code=code, center__isnull=True, allowed=False).exists():
        return False
    center_id = getattr(center, 'id', center)
    if center_id and PermissionOverride.objects.filter(
        role=role, code=code, center_id=center_id, allowed=False,
    ).exists():
        return False
    return True


def has_permission(user, code, center=None):
    """Return whether `user` may use `code`. This reads current rows, not the token."""

    if not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False):
        return False
    return role_has_permission(user.role, code, center or getattr(user, 'center', None))


def explain_role(role, center=None):
    """Describe every catalog code for one role."""

    from apps.common.models import PermissionOverride

    rows = []
    center_id = getattr(center, 'id', center)
    for spec in CATALOG.values():
        base = {
            'code': spec.code,
            'protected': spec.protected,
            'configurable': not spec.protected and role in spec.ceiling,
            'scope': spec.scope,
            'conditions': spec.conditions,
            'description': spec.description,
        }
        if role not in spec.ceiling:
            rows.append({**base, 'allowed': False, 'source': 'outside_ceiling'})
            continue
        if spec.protected:
            rows.append({**base, 'allowed': True, 'source': 'protected'})
            continue
        if PermissionOverride.objects.filter(role=role, code=spec.code, center__isnull=True, allowed=False).exists():
            rows.append({**base, 'allowed': False, 'source': 'global_restriction'})
            continue
        if center_id and PermissionOverride.objects.filter(
            role=role, code=spec.code, center_id=center_id, allowed=False,
        ).exists():
            rows.append({**base, 'allowed': False, 'source': 'center_restriction'})
            continue
        rows.append({**base, 'allowed': True, 'source': 'default'})
    return rows


def explain_permissions(user, center=None):
    """Effective permissions for the signed-in user."""

    center = center or getattr(user, 'center', None)
    return explain_role(user.role, center)


def permission_matrix(center=None):
    """Catalog rows with one cell per role."""

    roles = [Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER, Role.TEACHER, Role.STUDENT]
    explained = {role: {row['code']: row for row in explain_role(role, center)} for role in roles}
    rows = []
    for spec in CATALOG.values():
        rows.append({
            'code': spec.code,
            'protected': spec.protected,
            'description': spec.description,
            'scope': spec.scope,
            'conditions': spec.conditions,
            'ceiling': sorted(spec.ceiling),
            'cells': {
                role: {
                    'allowed': explained[role][spec.code]['allowed'],
                    'source': explained[role][spec.code]['source'],
                    'configurable': explained[role][spec.code]['configurable'],
                }
                for role in roles
            },
        })
    return {'roles': roles, 'rows': rows, 'lockout': LOCKOUT_NOTE}


def _guard_change(*, actor, role, code, center):
    from rest_framework.exceptions import PermissionDenied

    from apps.common.choices import Role
    from apps.common.exceptions import BusinessRuleError

    spec = CATALOG.get(code)
    if spec is None:
        raise BusinessRuleError('Unknown permission.')
    if spec.protected:
        raise BusinessRuleError('This separation of duties cannot be changed in settings.')
    if role not in spec.ceiling:
        raise BusinessRuleError('That role is outside the permission ceiling.')
    if actor.role == Role.SUPER_ADMIN:
        return spec
    if actor.role == Role.CENTER_MANAGER:
        if center is None or actor.center_id != getattr(center, 'id', center):
            raise PermissionDenied('A center manager can narrow permissions only for their own center.')
        if role == Role.SUPER_ADMIN:
            raise PermissionDenied('Center settings cannot change the super admin.')
        return spec
    raise PermissionDenied('You cannot change permissions.')


def preview_permission_change(*, actor, role, code, allowed, center=None, reason=''):
    """Describe a change without writing it."""

    from apps.accounts.models import User
    from apps.common.exceptions import BusinessRuleError

    spec = _guard_change(actor=actor, role=role, code=code, center=center)
    if len((reason or '').strip()) < 5:
        raise BusinessRuleError('A reason of at least 5 characters is required.')
    current = role_has_permission(role, code, center)
    people = User.objects.filter(role=role, is_active=True)
    if center is not None:
        people = people.filter(center_id=getattr(center, 'id', center))
    return {
        'code': code,
        'role': role,
        'center': getattr(center, 'id', None),
        'protected': spec.protected,
        'current_allowed': current,
        'proposed_allowed': bool(allowed),
        'changed': current != bool(allowed),
        'people': people.count(),
        'closes': [] if allowed else CLOSED_ROUTES.get(code, []),
        'lockout': False,
        'lockout_note': LOCKOUT_NOTE,
        'effect': 'The next request uses this result. Access tokens do not cache permissions.',
        'reason': reason.strip(),
    }


def set_permission_override(*, actor, role, code, allowed, center=None, request=None, reason='', restores=None):
    """Store a restriction, or remove it when `allowed` restores the default."""

    from django.db import transaction

    from apps.common.audit import write_audit
    from apps.common.exceptions import BusinessRuleError
    from apps.common.models import PermissionChange, PermissionOverride

    preview = preview_permission_change(
        actor=actor, role=role, code=code, allowed=allowed, center=center, reason=reason,
    )
    if not preview['changed']:
        raise BusinessRuleError('That permission is already in the requested state.')
    with transaction.atomic():
        latest = PermissionChange.objects.select_for_update().order_by('-version').first()
        version = (latest.version + 1) if latest else 1
        change = PermissionChange.objects.create(
            version=version,
            actor=actor,
            reason=reason.strip(),
            role=role,
            code=code,
            center=center,
            previous_allowed=preview['current_allowed'],
            allowed=bool(allowed),
            details={'closes': preview['closes'], 'restores': restores, 'people': preview['people']},
        )
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
        f'{code} for {role} {state} in version {change.version}.',
        user=actor,
        center=center,
        entity='permission',
        entity_id=str(change.version),
    )
    change.state = state
    return change


def restore_permission_change(*, actor, version, reason, request=None):
    """Apply the previous value of a stored version as a new version."""

    from apps.common.exceptions import BusinessRuleError
    from apps.common.models import PermissionChange

    original = PermissionChange.objects.filter(version=version).select_related('center').first()
    if original is None:
        raise BusinessRuleError('That permission version was not found.')
    return set_permission_override(
        actor=actor,
        role=original.role,
        code=original.code,
        allowed=original.previous_allowed,
        center=original.center,
        request=request,
        reason=reason,
        restores=original.version,
    )
