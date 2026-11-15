"""People, profiles, contracts, and password-reset tokens.

A person has one role and at most one center. Staff contracts use two unique
lock columns so the database itself rejects a second active contract or a
second active manager for the same center. NULL locks do not collide, which
is what lets expired and terminated contracts remain in history.
"""

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.choices import (
    STAFF_CONTRACT_ROLES,
    ContractStatus,
    ContractType,
    Gender,
    PaymentMethod,
    Role,
    SalaryType,
)
from apps.common.models import TimeStampedModel
from apps.common.validators import contract_window_error


def profile_photo_path(instance, filename):
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    if extension not in {'jpg', 'jpeg', 'png', 'webp'}:
        extension = 'jpg'
    return f'profiles/{uuid.uuid4().hex}.{extension}'


class UserManager(BaseUserManager):
    """Create users with a normalized email. Role and gender come from the caller."""

    def create_user(self, username, email=None, password=None, **extra):
        if not username:
            raise ValueError('Username is required.')
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email).lower()
        user = self.model(username=username.strip(), email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', Role.SUPER_ADMIN)
        extra.setdefault('gender', Gender.MALE)
        extra.setdefault('is_active', True)
        if extra.get('role') != Role.SUPER_ADMIN:
            raise ValueError('A Django superuser must use the super admin role.')
        return self.create_user(username, email, password, **extra)


class User(AbstractUser):
    """Authenticated person. `role` is the source of truth for API authorization."""

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.STUDENT, db_index=True)
    center = models.ForeignKey(
        'centers.Center',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='members',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    REQUIRED_FIELDS = ['email']

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(gender__in=[Gender.MALE, Gender.FEMALE]),
                name='user_gender_male_or_female',
            ),
            models.CheckConstraint(
                check=models.Q(role__in=[choice for choice, _label in Role.choices]),
                name='user_role_known',
            ),
            models.CheckConstraint(
                check=~models.Q(role=Role.SUPER_ADMIN) | models.Q(center__isnull=True),
                name='super_admin_has_no_center',
            ),
        ]
        indexes = [models.Index(fields=['role', 'center'])]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        name = f'{self.first_name} {self.last_name}'.strip()
        return name or self.username


class Profile(TimeStampedModel):
    """Personal details and the profile photo shown in the shell and tables."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to=profile_photo_path, null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'Profile of {self.user}'


class Contract(TimeStampedModel):
    """Employment contract for a manager, finance manager, or teacher.

    `active_user_lock` is the user id while the contract is active, else NULL.
    `active_manager_lock` is the center id only for an active center-manager
    contract. Both columns are unique, so a person cannot hold two active
    contracts and a center cannot have two active managers.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='contracts')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='contracts')
    contract_type = models.CharField(max_length=20, choices=ContractType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    salary_type = models.CharField(max_length=20, choices=SalaryType.choices)
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.ACTIVE,
        db_index=True,
    )
    notes = models.TextField(blank=True)
    active_user_lock = models.PositiveIntegerField(null=True, blank=True, unique=True)
    active_manager_lock = models.PositiveIntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ['-start_date']
        constraints = [
            models.CheckConstraint(
                check=models.Q(contract_type__in=[ContractType.YEARLY, ContractType.SIX_MONTHS]),
                name='contract_type_yearly_or_six_months',
            ),
            models.CheckConstraint(
                check=models.Q(salary_type__in=[SalaryType.HOURLY, SalaryType.MONTHLY]),
                name='salary_type_hourly_or_monthly',
            ),
            models.CheckConstraint(
                check=models.Q(payment_method__in=[PaymentMethod.CASH, PaymentMethod.BANK]),
                name='contract_payment_cash_or_bank',
            ),
            models.CheckConstraint(
                check=models.Q(status__in=[choice for choice, _label in ContractStatus.choices]),
                name='contract_status_known',
            ),
            models.CheckConstraint(check=models.Q(salary_amount__gt=0), name='contract_salary_positive'),
        ]
        indexes = [models.Index(fields=['center', 'status'])]

    def __str__(self):
        return f'{self.user} @ {self.center} ({self.status})'

    def clean(self):
        message = contract_window_error(self.contract_type, self.start_date, self.end_date)
        if message:
            raise ValidationError(message)
        if self.user_id and self.user.role not in STAFF_CONTRACT_ROLES:
            raise ValidationError('Contracts apply only to managers, finance managers, and teachers.')

    def save(self, *args, **kwargs):
        # An ended date can never stay active, even if a caller forgets to expire it.
        if self.status == ContractStatus.ACTIVE and self.end_date and self.end_date < timezone.localdate():
            self.status = ContractStatus.EXPIRED
        if self.status == ContractStatus.ACTIVE:
            self.active_user_lock = self.user_id
            role = self.user.role if self.user_id else None
            self.active_manager_lock = self.center_id if role == Role.CENTER_MANAGER else None
        else:
            self.active_user_lock = None
            self.active_manager_lock = None
        super().save(*args, **kwargs)


class PasswordResetToken(TimeStampedModel):
    """Single-use reset secret. Only the SHA-256 digest is stored."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'expires_at'])]
