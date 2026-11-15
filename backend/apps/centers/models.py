"""Centers, their operational settings, and the single global settings row.

A center is the isolation boundary for every other record. It does not store
a direct manager foreign key: the active manager is the user whose active
contract holds this center in `active_manager_lock`. That keeps "exactly one
active manager" as a database unique value instead of a pair of pointers that
can drift apart.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


def center_logo_path(instance, filename):
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    if extension not in {'jpg', 'jpeg', 'png', 'webp'}:
        extension = 'jpg'
    return f'centers/{uuid.uuid4().hex}.{extension}'


class Center(SoftDeleteModel):
    """A tuition center. Day-to-day data never crosses this boundary."""

    name = models.CharField(max_length=180)
    code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to=center_logo_path, null=True, blank=True)
    description = models.TextField(blank=True)
    # Inactive until a manager is assigned and the super admin activates it.
    is_active = models.BooleanField(default=False, db_index=True)
    established_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['is_active', 'city'])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    def get_active_manager(self):
        """Return the single active center manager, using a prefetch when present."""

        prefetched = getattr(self, '_prefetched_manager', None)
        if prefetched is not None:
            from django.utils import timezone

            today = timezone.localdate()
            contract = next((
                row for row in prefetched
                if row.user.is_active and row.start_date <= today <= row.end_date
            ), None)
            return contract.user if contract else None
        from apps.accounts.models import Contract

        from django.utils import timezone

        today = timezone.localdate()
        contract = (
            Contract.objects.select_related('user', 'user__profile')
            .filter(
                center=self,
                status='active',
                active_manager_lock=self.id,
                user__is_active=True,
                start_date__lte=today,
                end_date__gte=today,
            )
            .first()
        )
        return contract.user if contract else None


class CenterSettings(TimeStampedModel):
    """Per-center rules that the manager may change inside the global ceiling."""

    center = models.OneToOneField(Center, on_delete=models.CASCADE, related_name='settings')
    allow_self_enrollment = models.BooleanField(default=True)
    require_enrollment_approval = models.BooleanField(default=False)
    allow_waitlist = models.BooleanField(default=True)
    allow_student_refund_requests = models.BooleanField(default=True)
    allow_finance_refund_requests = models.BooleanField(default=True)
    # Hard product cap is 3. The global setting can lower it further.
    max_installments = models.PositiveSmallIntegerField(default=3)

    class Meta:
        verbose_name_plural = 'center settings'
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_installments__gte=1, max_installments__lte=3),
                name='center_installment_cap',
            ),
        ]

    def __str__(self):
        return f'Settings for {self.center}'

    def clean(self):
        cap = min(3, GlobalSettings.load().max_installments)
        if not 1 <= self.max_installments <= cap:
            raise ValidationError(f'Installments must be between 1 and {cap}.')


class GlobalSettings(TimeStampedModel):
    """Organization-wide rules owned by the super admin. One row only."""

    organization_name = models.CharField(max_length=180, default='Course Tuition Center MIS')
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)
    # Display label only. Amounts are AFN and this value cannot be changed.
    currency_label = models.CharField(max_length=12, default='AFN')
    default_allow_self_enrollment = models.BooleanField(default=True)
    allow_self_enrollment = models.BooleanField(default=True)
    require_enrollment_approval = models.BooleanField(default=False)
    allow_waitlist = models.BooleanField(default=True)
    allow_student_refund_requests = models.BooleanField(default=True)
    allow_finance_refund_requests = models.BooleanField(default=True)
    max_installments = models.PositiveSmallIntegerField(default=3)

    class Meta:
        verbose_name_plural = 'global settings'
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_installments__gte=1, max_installments__lte=3),
                name='global_installment_cap',
            ),
        ]

    def clean(self):
        if (self.currency_label or '').strip().upper() != 'AFN':
            raise ValidationError('Amounts are AFN. The currency label cannot name another currency.')
        self.currency_label = 'AFN'

    def save(self, *args, **kwargs):
        self.pk = 1
        self.currency_label = 'AFN'
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class PolicyRevision(TimeStampedModel):
    """Immutable copy of a policy after each change. Older invoices are not rewritten."""

    GLOBAL = 'global'
    CENTER = 'center'
    SCOPE_CHOICES = [(GLOBAL, 'Global'), (CENTER, 'Center')]

    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
    center = models.ForeignKey(Center, null=True, blank=True, on_delete=models.CASCADE, related_name='policy_revisions')
    version = models.PositiveIntegerField()
    payload = models.JSONField(default=dict)
    note = models.CharField(max_length=240, blank=True)
    actor = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='policy_revisions',
    )

    class Meta:
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(
                fields=['scope', 'version'],
                condition=models.Q(center__isnull=True),
                name='unique_global_policy_revision',
            ),
            models.UniqueConstraint(
                fields=['scope', 'center', 'version'],
                condition=models.Q(center__isnull=False),
                name='unique_center_policy_revision',
            ),
        ]
