"""Center lifecycle and manager assignment.

A center may have one active manager. The person offered in the assignment
list has no active contract. Replacing a manager ends the previous contract
and writes the new one in a single transaction, so the center never keeps two.
"""

import re

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Contract, User
from apps.accounts.services import active_contract_for, create_contract, refresh_expired_contracts, terminate_contract
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import ContractStatus, Role
from apps.common.exceptions import BusinessRuleError
from apps.common.images import validate_image
from apps.centers.models import Center, GlobalSettings

CODE_PATTERN = re.compile(r'^[A-Z0-9]{2,20}$')


def visible_centers(user):
    """Centers this user is allowed to see. Super admin sees all live centers."""

    queryset = Center.objects.filter(is_deleted=False)
    if user.role == Role.SUPER_ADMIN:
        return queryset
    if user.center_id:
        return queryset.filter(pk=user.center_id)
    return queryset.none()


def available_managers():
    """Center managers who are not currently contracted to any center."""

    refresh_expired_contracts()
    busy_ids = Contract.objects.filter(status=ContractStatus.ACTIVE).values_list('user_id', flat=True)
    return (
        User.objects.filter(role=Role.CENTER_MANAGER, is_active=True)
        .exclude(id__in=busy_ids)
        .select_related('profile')
        .order_by('first_name', 'last_name')
    )


def create_center(data, actor, request=None):
    """Create an inactive center. It cannot be activated until a manager is assigned."""

    if actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('Only the super admin can create a center.')
    code = data['code'].strip().upper()
    if not CODE_PATTERN.match(code):
        raise BusinessRuleError('Center code must be 2 to 20 letters or digits.')
    if Center.objects.filter(code=code).exists():
        raise BusinessRuleError('A center with this code already exists.')
    center = Center.objects.create(
        name=data['name'].strip(),
        code=code,
        address=data.get('address', '') or '',
        city=data.get('city', '') or '',
        phone=data.get('phone', '') or '',
        email=data.get('email', '') or '',
        description=data.get('description', '') or '',
        established_on=data.get('established_on'),
        is_active=False,
    )
    settings = center.settings
    settings.allow_self_enrollment = GlobalSettings.load().default_allow_self_enrollment
    settings.save(update_fields=['allow_self_enrollment', 'updated_at'])
    write_audit(request, 'center.create', f'Created center {center.code}.', user=actor, center=center, entity='center', entity_id=center.id)
    return center


def update_center(center, data, actor, request=None):
    """Super admin edits identity fields. The manager edits contact details only."""

    if actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, center, request)
        allowed = {'name', 'address', 'city', 'phone', 'email', 'description'}
    elif actor.role == Role.SUPER_ADMIN:
        allowed = {'name', 'address', 'city', 'phone', 'email', 'description', 'code', 'established_on'}
    else:
        raise PermissionDenied('You cannot edit this center.')
    if 'code' in data and 'code' in allowed:
        code = data['code'].strip().upper()
        if not CODE_PATTERN.match(code):
            raise BusinessRuleError('Center code must be 2 to 20 letters or digits.')
        if Center.objects.exclude(pk=center.pk).filter(code=code).exists():
            raise BusinessRuleError('A center with this code already exists.')
        data = {**data, 'code': code}
    for key, value in data.items():
        if key in allowed:
            setattr(center, key, value)
    center.save()
    write_audit(request, 'center.update', f'Updated center {center.code}.', user=actor, center=center, entity='center', entity_id=center.id)
    return center


def set_center_logo(center, upload, actor, request=None):
    """Store a center logo. Same image rules as a profile photo."""

    if actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, center, request)
    elif actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('You cannot change this logo.')
    validate_image(upload)
    if center.logo:
        center.logo.delete(save=False)
    center.logo = upload
    center.save()
    return center


def set_center_active(center, active, actor, request=None):
    """Activation requires the single active manager. Deactivation is immediate."""

    if actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('Only the super admin can activate or deactivate a center.')
    if active and center.get_active_manager() is None:
        raise BusinessRuleError('Assign a center manager before activating the center.')
    center.is_active = active
    center.save(update_fields=['is_active', 'updated_at'])
    write_audit(
        request,
        'center.active' if active else 'center.inactive',
        f'{center.code} is now {"active" if active else "inactive"}.',
        user=actor,
        center=center,
        entity='center',
        entity_id=center.id,
    )
    return center


def archive_center(center, actor, request=None):
    """Hide a deactivated center from lists without deleting its history."""

    if actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('Only the super admin can archive a center.')
    if center.is_active:
        raise BusinessRuleError('Deactivate the center before archiving it.')
    center.archive()
    write_audit(request, 'center.archive', f'Archived {center.code}.', user=actor, center=center, entity='center', entity_id=center.id)
    return center


def assign_manager(*, center, manager, contract_data, actor, replace=False, request=None):
    """Attach one manager. Busy managers and a second active manager are refused."""

    if actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('Only the super admin can assign a center manager.')
    if manager.role != Role.CENTER_MANAGER or not manager.is_active:
        raise BusinessRuleError('Select an active center manager.')
    with transaction.atomic():
        center = Center.objects.select_for_update().get(pk=center.pk)
        if center.is_deleted:
            raise BusinessRuleError('Archived centers cannot take a new manager.')
        refresh_expired_contracts(manager)
        active = active_contract_for(manager)
        if active and active.center_id != center.id:
            raise BusinessRuleError('This manager still has an active contract at another center.')
        if active and active.center_id == center.id:
            raise BusinessRuleError('This manager is already assigned to this center.')
        current = center.get_active_manager()
        if current and current.id != manager.id:
            if not replace:
                raise BusinessRuleError('This center already has an active manager. Confirm replacement to continue.')
            current_contract = Contract.objects.select_for_update().get(user=current, status=ContractStatus.ACTIVE)
            terminate_contract(current_contract, actor, force=True, request=request)
        contract = create_contract(manager, center, contract_data, actor, request=request)
    write_audit(
        request,
        'center.assign_manager',
        f'{manager.username} assigned to {center.code}.',
        user=actor,
        center=center,
        entity='center',
        entity_id=center.id,
    )
    return contract


def update_center_settings(settings_obj, data, actor, request=None):
    """Update enrollment and installment settings inside the global ceiling."""

    if actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, settings_obj.center, request)
    elif actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('You cannot edit these settings.')
    for field in ('allow_self_enrollment', 'require_enrollment_approval', 'max_installments'):
        if field in data:
            setattr(settings_obj, field, data[field])
    cap = min(3, GlobalSettings.load().max_installments)
    if not 1 <= int(settings_obj.max_installments) <= cap:
        raise BusinessRuleError(f'Installments must be between 1 and {cap}.')
    settings_obj.full_clean()
    settings_obj.save()
    return settings_obj


def update_global_settings(data, actor):
    """Super admin organization defaults. The installment ceiling cannot exceed 3."""

    if actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('Only the super admin can change global settings.')
    settings_obj = GlobalSettings.load()
    for field in (
        'organization_name',
        'support_email',
        'support_phone',
        'currency_label',
        'default_allow_self_enrollment',
        'max_installments',
    ):
        if field in data:
            setattr(settings_obj, field, data[field])
    if not 1 <= int(settings_obj.max_installments) <= 3:
        raise BusinessRuleError('The global installment maximum must be between 1 and 3.')
    settings_obj.full_clean()
    settings_obj.save()
    return settings_obj


def center_statistics(center):
    """Counts and an all-time finance snapshot for one center."""

    from apps.classes.models import CourseClass
    from apps.common.choices import CourseStatus
    from apps.courses.models import Course
    from apps.finance.services import build_snapshot

    members = User.objects.filter(center=center, is_active=True)
    return {
        'students': members.filter(role=Role.STUDENT).count(),
        'teachers': members.filter(role=Role.TEACHER).count(),
        'finance_managers': members.filter(role=Role.FINANCE_MANAGER).count(),
        'courses': Course.objects.filter(center=center, is_deleted=False).count(),
        'active_courses': Course.objects.filter(center=center, is_deleted=False, status=CourseStatus.ACTIVE).count(),
        'classes': CourseClass.objects.filter(center=center, is_deleted=False).count(),
        'manager': _manager_payload(center),
        'finance': build_snapshot(center),
    }


def _manager_payload(center):
    manager = center.get_active_manager()
    if manager is None:
        return None
    return {
        'id': manager.id,
        'full_name': manager.full_name,
        'email': manager.email,
        'phone': manager.phone,
    }
