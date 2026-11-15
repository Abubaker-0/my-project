"""Invoices, payments, installments, scholarships, and refunds.

Money fields are decimals. Payment method is only cash or bank. An installment
number cannot be outside 1..3, which is also the product maximum.
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.common.choices import (
    InstallmentStatus,
    InvoiceStatus,
    PaymentMethod,
    RefundStatus,
    ScholarshipType,
)
from apps.common.models import TimeStampedModel


def compute_installment_status(paid, amount, due_date, today=None):
    """Map amounts and the due date to the only four installment statuses.

    A past-due installment that is not fully paid is overdue, even when a
    partial payment exists. Fully paid installments stay paid.
    """

    today = today or timezone.localdate()
    paid = Decimal(paid or 0)
    amount = Decimal(amount or 0)
    if paid >= amount:
        return InstallmentStatus.PAID
    if due_date < today:
        return InstallmentStatus.OVERDUE
    if paid > 0:
        return InstallmentStatus.PARTIALLY_PAID
    return InstallmentStatus.PENDING


class Invoice(TimeStampedModel):
    """The payable fee for one enrollment, after a scholarship if one is applied."""

    invoice_number = models.CharField(max_length=40, unique=True)
    enrollment = models.OneToOneField(
        'enrollments.Enrollment',
        on_delete=models.PROTECT,
        related_name='invoice',
    )
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='invoices')
    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='invoices')
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    scholarship_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['center', 'status'])]
        constraints = [
            models.CheckConstraint(check=models.Q(gross_amount__gte=0), name='invoice_gross_non_negative'),
            models.CheckConstraint(check=models.Q(net_amount__gte=0), name='invoice_net_non_negative'),
            models.CheckConstraint(check=models.Q(paid_amount__gte=0), name='invoice_paid_non_negative'),
            models.CheckConstraint(check=models.Q(refunded_amount__gte=0), name='invoice_refunded_non_negative'),
        ]

    def __str__(self):
        return self.invoice_number

    @property
    def outstanding(self):
        from apps.common.money import money

        return money(max(money(self.net_amount) - money(self.paid_amount), 0))

    @property
    def refund_state(self):
        """Collection status stays on `status`. Refund progress is reported separately."""

        from apps.common.money import money

        refunded = money(self.refunded_amount)
        paid = money(self.paid_amount)
        if refunded <= 0:
            return 'none'
        if paid > 0 and refunded >= paid:
            return 'full'
        return 'partial'


class Payment(TimeStampedModel):
    """Cash or bank receipt against an invoice. There is no exchange rate."""

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='payments')
    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    reference = models.CharField(max_length=80, blank=True)
    receipt_number = models.CharField(max_length=40, unique=True, null=True, blank=True)
    idempotency_key = models.CharField(max_length=80, null=True, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='payments_received',
    )

    class Meta:
        ordering = ['-paid_at']
        indexes = [models.Index(fields=['center', 'paid_at'])]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='payment_amount_positive'),
            models.CheckConstraint(
                check=models.Q(method__in=[PaymentMethod.CASH, PaymentMethod.BANK]),
                name='payment_method_cash_or_bank',
            ),
            models.UniqueConstraint(
                fields=['received_by', 'idempotency_key'],
                name='unique_payment_idempotency',
            ),
        ]

    def __str__(self):
        return f'{self.method} {self.amount} on {self.invoice_id}'


class Installment(TimeStampedModel):
    """One slice of an invoice. A plan contains at most three slices."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='installments')
    number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=InstallmentStatus.choices, default=InstallmentStatus.PENDING)

    class Meta:
        ordering = ['number']
        constraints = [
            models.UniqueConstraint(fields=['invoice', 'number'], name='unique_installment_number'),
            models.CheckConstraint(
                check=models.Q(number__gte=1, number__lte=3),
                name='installment_number_one_to_three',
            ),
            models.CheckConstraint(check=models.Q(amount__gte=0), name='installment_amount_non_negative'),
            models.CheckConstraint(check=models.Q(paid_amount__gte=0), name='installment_paid_non_negative'),
        ]

    def __str__(self):
        return f'{self.invoice.invoice_number} #{self.number}'

    def save(self, *args, **kwargs):
        # Status is derived so a client cannot store an unknown value.
        self.status = compute_installment_status(self.paid_amount, self.amount, self.due_date)
        super().save(*args, **kwargs)


class Scholarship(TimeStampedModel):
    """A center-defined discount, either a percentage or a fixed amount."""

    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='scholarships')
    name = models.CharField(max_length=160)
    scholarship_type = models.CharField(max_length=20, choices=ScholarshipType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(check=models.Q(value__gte=0), name='scholarship_value_non_negative'),
            models.CheckConstraint(
                check=models.Q(scholarship_type__in=[ScholarshipType.PERCENTAGE, ScholarshipType.FIXED]),
                name='scholarship_type_percentage_or_fixed',
            ),
        ]

    def __str__(self):
        return self.name


class ScholarshipGrant(TimeStampedModel):
    """The scholarship actually applied to one enrollment."""

    scholarship = models.ForeignKey(Scholarship, on_delete=models.PROTECT, related_name='grants')
    enrollment = models.OneToOneField(
        'enrollments.Enrollment',
        on_delete=models.PROTECT,
        related_name='scholarship_grant',
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='grants')
    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='scholarship_grants')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='scholarship_grants')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    granted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='scholarships_granted',
    )

    def __str__(self):
        return f'{self.scholarship} for {self.student}'


class InstallmentPlanArchive(TimeStampedModel):
    """Preserved copy of an unpaid plan that finance replaced."""

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='plan_archives')
    payload = models.JSONField(default=list)
    replaced_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='installment_plan_archives')


class Refund(TimeStampedModel):
    """A refund request. Only the center manager can approve or reject it."""

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='refunds')
    center = models.ForeignKey('centers.Center', on_delete=models.PROTECT, related_name='refunds')
    student = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RefundStatus.choices, default=RefundStatus.PENDING)
    requested_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='refunds_requested',
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='refunds_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['center', 'status'])]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='refund_amount_positive'),
            models.CheckConstraint(
                check=models.Q(status__in=[choice for choice, _label in RefundStatus.choices]),
                name='refund_status_known',
            ),
        ]

    def __str__(self):
        return f'Refund {self.amount} ({self.status})'
