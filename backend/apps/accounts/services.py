"""Account, profile, and contract rules.

Creating a person, moving them between centers, and ending a contract all go
through this module so views cannot bypass the one-center and one-active-contract
rules. Super admin can create and assign center managers only. A center manager
can create finance managers, teachers, and students inside their own center.
"""

import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Contract, PasswordResetToken, User
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import STAFF_CONTRACT_ROLES, ContractStatus, Role
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.common.images import validate_image
from apps.common.validators import contract_window_error


def creator_error(actor, role):
    """Return a message when this actor is not allowed to create `role`."""

    if actor.role == Role.SUPER_ADMIN and role != Role.CENTER_MANAGER:
        return 'Super admin can only create center managers.'
    if actor.role == Role.CENTER_MANAGER and role not in (
        Role.FINANCE_MANAGER,
        Role.TEACHER,
        Role.STUDENT,
    ):
        return 'Center managers can create finance managers, teachers, and students.'
    if actor.role not in (Role.SUPER_ADMIN, Role.CENTER_MANAGER):
        return 'You cannot create users.'
    return ''


def refresh_expired_contracts(user=None):
    """Mark active contracts whose end date has passed as expired.

    Called before assignment and contract checks so a lapsed contract does not
    keep a manager or teacher locked to a center.
    """

    today = timezone.localdate()
    queryset = Contract.objects.filter(status=ContractStatus.ACTIVE, end_date__lt=today)
    if user is not None:
        queryset = queryset.filter(user=user)
    for contract in queryset.select_related('user'):
        contract.status = ContractStatus.EXPIRED
        contract.save()


def active_contract_for(user):
    """Return the user's active contract after expiring lapsed ones."""

    refresh_expired_contracts(user)
    return (
        Contract.objects.filter(user=user, status=ContractStatus.ACTIVE)
        .select_related('center')
        .first()
    )


def assert_operational(user):
    """Block day-to-day writes when the center or staff contract is not active.

    Students do not have contracts. Super admin is rejected here because course,
    class, money, and attendance work belongs to the center, not to head office.
    """

    if user.role == Role.SUPER_ADMIN:
        raise PermissionDenied('Super admin cannot perform day-to-day center operations.')
    if not user.is_active:
        raise BusinessRuleError('Your account is inactive.')
    center = user.center
    if center is None or center.is_deleted or not center.is_active:
        raise BusinessRuleError('Your center is inactive.')
    if user.role != Role.STUDENT and active_contract_for(user) is None:
        raise BusinessRuleError('Your contract is not active.')


def _check_password(password, user=None):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise BusinessRuleError(' '.join(exc.messages)) from exc


def create_account(data, actor, request=None):
    """Create a user and, for finance managers and teachers, their first contract.

    Center managers are created without a center. The super admin assigns them
    from the center screen, and that assignment is what creates their contract.
    Students and staff created by a manager are pinned to the manager's center.
    """

    message = creator_error(actor, data['role'])
    if message:
        raise PermissionDenied(message)
    role = data['role']
    center = None
    if actor.role == Role.CENTER_MANAGER:
        if actor.center_id is None:
            raise BusinessRuleError('Your account is not assigned to a center.')
        center = actor.center
        assert_operational(actor)
    if role in (Role.TEACHER, Role.FINANCE_MANAGER) and not data.get('contract'):
        raise BusinessRuleError('A contract is required for this role.')
    if role == Role.STUDENT and data.get('contract'):
        raise BusinessRuleError('Students do not receive a staff contract.')
    _check_password(data['password'])
    with transaction.atomic():
        user = User(
            username=data['username'].strip(),
            email=data['email'],
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            phone=data['phone'].strip(),
            gender=data['gender'],
            role=role,
            center=center,
            is_active=True,
        )
        user.set_password(data['password'])
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError as exc:
            raise ConflictError('Username or email is already in use.') from exc
        profile = user.profile
        profile.address = data.get('address', '') or ''
        profile.save(update_fields=['address', 'updated_at'])
        if role in (Role.TEACHER, Role.FINANCE_MANAGER):
            create_contract(user, center, data['contract'], actor, request=request)
    write_audit(
        request,
        'user.create',
        f'Created {role} {user.username}.',
        user=actor,
        center=user.center,
        entity='user',
        entity_id=user.id,
    )
    return user


def update_account(user, data, actor, request=None):
    """Update another person's basic details. Role and center stay unchanged."""

    if actor.id == user.id:
        raise PermissionDenied('Update your own details from the profile page.')
    if actor.role == Role.SUPER_ADMIN:
        if user.role != Role.CENTER_MANAGER:
            raise PermissionDenied('Super admin can edit center manager accounts.')
    elif actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, user.center_id, request)
        if user.role == Role.CENTER_MANAGER:
            raise PermissionDenied('You cannot edit the center manager account.')
        assert_operational(actor)
    else:
        raise PermissionDenied('You cannot edit this account.')
    for field in ('first_name', 'last_name', 'phone', 'gender', 'email'):
        if field in data and data[field] is not None:
            setattr(user, field, data[field].strip() if isinstance(data[field], str) else data[field])
    try:
        user.save()
    except IntegrityError as exc:
        raise ConflictError('That email is already in use.') from exc
    profile = user.profile
    for field in ('address', 'bio', 'date_of_birth'):
        if field in data:
            setattr(profile, field, data[field] or '')
    profile.save()
    write_audit(request, 'user.update', f'Updated {user.username}.', user=actor, center=user.center, entity='user', entity_id=user.id)
    return user


def change_role(user, new_role, actor, request=None):
    """Change a center staff role only when no contract or enrollment is open.

    Center manager and super admin roles are assigned by dedicated flows, not
    by this action, so a manager cannot promote themselves.
    """

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only a center manager can change staff roles.')
    assert_same_center(actor, user.center_id, request)
    assert_operational(actor)
    if user.id == actor.id:
        raise BusinessRuleError('You cannot change your own role.')
    if new_role not in (Role.FINANCE_MANAGER, Role.TEACHER, Role.STUDENT):
        raise BusinessRuleError('You can assign finance manager, teacher, or student.')
    if user.role in (Role.SUPER_ADMIN, Role.CENTER_MANAGER):
        raise BusinessRuleError('That role cannot be changed here.')
    if user.role == new_role:
        return user
    if Contract.objects.filter(user=user, status=ContractStatus.ACTIVE).exists():
        raise BusinessRuleError('End the active contract before changing the role.')
    from apps.common.choices import OPEN_ENROLLMENT
    from apps.enrollments.models import Enrollment

    if Enrollment.objects.filter(student=user, status__in=OPEN_ENROLLMENT).exists():
        raise BusinessRuleError('Close active enrollments before changing the role.')
    user.role = new_role
    user.save(update_fields=['role', 'updated_at'])
    write_audit(request, 'user.role', f'{user.username} is now {new_role}.', user=actor, center=user.center, entity='user', entity_id=user.id)
    return user


def deactivate_user(user, actor, request=None):
    """Deactivate a person. An active center keeps its only manager."""

    if user.id == actor.id or user.role == Role.SUPER_ADMIN:
        raise BusinessRuleError('This account cannot be deactivated.')
    if actor.role == Role.SUPER_ADMIN:
        if user.role != Role.CENTER_MANAGER:
            raise PermissionDenied('Super admin deactivates center managers. The center handles its own staff.')
    elif actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, user.center_id, request)
        if user.role not in (Role.FINANCE_MANAGER, Role.TEACHER, Role.STUDENT):
            raise PermissionDenied('You cannot deactivate this account.')
        assert_operational(actor)
    else:
        raise PermissionDenied('You cannot deactivate accounts.')
    contract = Contract.objects.filter(user=user, status=ContractStatus.ACTIVE).select_related('center', 'user').first()
    if contract:
        terminate_contract(contract, actor, request=request)
    user.is_active = False
    user.save(update_fields=['is_active', 'updated_at'])
    write_audit(request, 'user.deactivate', f'Deactivated {user.username}.', user=actor, center=user.center, entity='user', entity_id=user.id)
    return user


def activate_user(user, actor, request=None):
    """Re-enable login. A new contract is still required before staff can work."""

    if actor.role == Role.SUPER_ADMIN:
        if user.role != Role.CENTER_MANAGER:
            raise PermissionDenied('Super admin can activate center managers.')
    elif actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, user.center_id, request)
        if user.role not in (Role.FINANCE_MANAGER, Role.TEACHER, Role.STUDENT):
            raise PermissionDenied('You cannot activate this account.')
    else:
        raise PermissionDenied('You cannot activate accounts.')
    user.is_active = True
    user.save(update_fields=['is_active', 'updated_at'])
    write_audit(request, 'user.activate', f'Activated {user.username}.', user=actor, center=user.center, entity='user', entity_id=user.id)
    return user


def create_contract(user, center, data, actor, request=None):
    """Open one contract. A second active contract is rejected for every role.

    A center manager contract also takes the center's single manager lock.
    Callers that are replacing a manager must terminate the previous contract
    in the same transaction before calling this function.
    """

    if user.role not in STAFF_CONTRACT_ROLES:
        raise BusinessRuleError('Contracts apply only to center managers, finance managers, and teachers.')
    if not user.is_active:
        raise BusinessRuleError('Inactive users cannot receive a contract.')
    if actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, center, request)
        assert_operational(actor)
        if user.role == Role.CENTER_MANAGER:
            raise PermissionDenied('Only the super admin can contract a center manager.')
    elif actor.role == Role.SUPER_ADMIN:
        if user.role != Role.CENTER_MANAGER:
            raise PermissionDenied('Super admin assigns contracts to center managers only.')
    else:
        raise PermissionDenied('You cannot create contracts.')
    if user.center_id not in (None, center.id):
        raise ConflictError('This user still belongs to another center.')
    message = contract_window_error(data['contract_type'], data['start_date'], data['end_date'])
    if message:
        raise BusinessRuleError(message)
    from apps.common.money import money
    if money(data['salary_amount']) <= 0:
        raise BusinessRuleError('Salary must be greater than zero.')
    refresh_expired_contracts(user)
    if Contract.objects.filter(user=user, status=ContractStatus.ACTIVE).exists():
        raise ConflictError('This user already has an active contract. End it before creating a new one.')
    if user.role == Role.CENTER_MANAGER and Contract.objects.filter(
        status=ContractStatus.ACTIVE,
        active_manager_lock=center.id,
    ).exclude(user=user).exists():
        raise ConflictError('This center already has an active manager.')
    contract = Contract(
        user=user,
        center=center,
        contract_type=data['contract_type'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        salary_type=data['salary_type'],
        salary_amount=data['salary_amount'],
        payment_method=data['payment_method'],
        status=ContractStatus.ACTIVE,
        notes=data.get('notes', '') or '',
    )
    contract.full_clean()
    try:
        with transaction.atomic():
            contract.save()
    except IntegrityError as exc:
        raise ConflictError('This user already has an active contract or the center already has a manager.') from exc
    if user.center_id != center.id:
        user.center = center
        user.save(update_fields=['center', 'updated_at'])
    write_audit(
        request,
        'contract.create',
        f'Contract opened for {user.username} at {center.code}.',
        user=actor,
        center=center,
        entity='contract',
        entity_id=contract.id,
    )
    return contract


def terminate_contract(contract, actor, *, force=False, request=None):
    """End an active contract.

    The only manager of an active center cannot be removed unless `force` is
    set by the replacement flow, which immediately writes a new manager in the
    same database transaction. Deactivating the center first is the other path.
    """

    if contract.status != ContractStatus.ACTIVE:
        raise BusinessRuleError('Only an active contract can be ended.')
    is_manager_contract = contract.user.role == Role.CENTER_MANAGER
    if actor.role == Role.CENTER_MANAGER:
        assert_same_center(actor, contract.center, request)
        if is_manager_contract:
            raise PermissionDenied('You cannot end the center manager contract.')
    elif actor.role != Role.SUPER_ADMIN:
        raise PermissionDenied('You cannot end this contract.')
    if is_manager_contract and contract.center.is_active and not force:
        raise BusinessRuleError(
            'Deactivate the center or assign a replacement manager before ending this contract.'
        )
    contract.status = ContractStatus.TERMINATED
    contract.save()
    if is_manager_contract and contract.user.center_id == contract.center_id:
        contract.user.center = None
        contract.user.save(update_fields=['center', 'updated_at'])
    write_audit(
        request,
        'contract.terminate',
        f'Contract ended for {contract.user.username}.',
        user=actor,
        center=contract.center,
        entity='contract',
        entity_id=contract.id,
    )
    return contract


def update_own_profile(user, data):
    """Fields a person may change on themselves. Role, center, and username stay fixed."""

    for field in ('first_name', 'last_name', 'phone', 'gender', 'email'):
        if field in data and data[field] is not None:
            setattr(user, field, data[field].strip() if isinstance(data[field], str) else data[field])
    try:
        user.save()
    except IntegrityError as exc:
        raise ConflictError('That email is already in use.') from exc
    profile = user.profile
    for field in ('address', 'bio', 'date_of_birth'):
        if field in data:
            setattr(profile, field, data[field] or '')
    profile.save()
    return user


def change_password(user, old_password, new_password):
    """Require the current password before replacing it."""

    if not user.check_password(old_password):
        raise BusinessRuleError('Current password is incorrect.')
    _check_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=['password', 'updated_at'])


def set_profile_photo(user, upload):
    """Replace the profile photo after the file passes image validation."""

    validate_image(upload)
    profile = user.profile
    if profile.photo:
        profile.photo.delete(save=False)
    profile.photo = upload
    profile.save()
    return profile


def request_password_reset(login):
    """Create a reset token when the account exists.

    The same outcome is returned either way so the endpoint cannot be used to
    discover usernames. The raw token is returned only to the view, which
    exposes it when DEBUG is on so the local demo can complete the flow.
    """

    user = User.objects.filter(Q(username__iexact=login) | Q(email__iexact=login), is_active=True).first()
    if user is None:
        return None
    raw = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    return raw


def reset_password(raw_token, new_password):
    """Consume a reset token and set a new password."""

    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    record = (
        PasswordResetToken.objects.filter(token_hash=digest, used_at__isnull=True, expires_at__gte=timezone.now())
        .select_related('user')
        .first()
    )
    if record is None:
        raise BusinessRuleError('This reset token is invalid or expired.')
    _check_password(new_password, record.user)
    record.user.set_password(new_password)
    record.user.save(update_fields=['password', 'updated_at'])
    record.used_at = timezone.now()
    record.save(update_fields=['used_at', 'updated_at'])
