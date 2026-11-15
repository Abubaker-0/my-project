"""Fees, payments, installments, scholarships, and refunds.

Finance managers record money for their own center. Refunds stay pending until
the center manager approves them. Amounts are decimal and payment methods are
only cash and bank. There is no currency conversion.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.services import assert_operational
from apps.common.access import assert_same_center
from apps.common.audit import write_audit
from apps.common.choices import (
    InstallmentStatus,
    InvoiceStatus,
    PaymentMethod,
    RefundStatus,
    Role,
    ScholarshipType,
)
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.common.money import money, money_str, split_amount
from apps.finance.models import (
    Installment,
    Invoice,
    Payment,
    Refund,
    Scholarship,
    ScholarshipGrant,
)


def refresh_invoice_status(invoice):
    """Set the invoice status from what has been collected and returned."""

    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice
    paid = money(invoice.paid_amount)
    refunded = money(invoice.refunded_amount)
    net = money(invoice.net_amount)
    if paid > 0 and refunded >= paid:
        invoice.status = InvoiceStatus.REFUNDED
    elif paid >= net:
        invoice.status = InvoiceStatus.PAID
    elif paid > 0:
        invoice.status = InvoiceStatus.PARTIAL
    else:
        invoice.status = InvoiceStatus.UNPAID
    return invoice


def installment_cap(center):
    """The smaller of the global cap, the center cap, and the hard maximum of 3."""

    from apps.centers.models import GlobalSettings

    global_cap = GlobalSettings.load().max_installments
    local_cap = center.settings.max_installments
    return max(1, min(3, global_cap, local_cap))


def _finance(actor, center, request):
    if actor.role != Role.FINANCE_MANAGER:
        raise PermissionDenied('Only the finance manager can change financial records.')
    assert_same_center(actor, center, request)
    assert_operational(actor)


def next_invoice_number(center):
    year = timezone.localdate().year
    prefix = f'INV-{center.code}-{year}-'
    last = (
        Invoice.objects.filter(invoice_number__startswith=prefix)
        .order_by('-invoice_number')
        .values_list('invoice_number', flat=True)
        .first()
    )
    sequence = 1
    if last:
        try:
            sequence = int(last.rsplit('-', 1)[-1]) + 1
        except ValueError:
            sequence = Invoice.objects.filter(invoice_number__startswith=prefix).count() + 1
    return f'{prefix}{sequence:04d}'


def ensure_invoice(enrollment):
    """Issue the fee invoice for an active enrollment. Safe to call twice."""

    try:
        return enrollment.invoice
    except Invoice.DoesNotExist:
        pass
    gross = money(enrollment.course.fee)
    for _attempt in range(5):
        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    invoice_number=next_invoice_number(enrollment.center),
                    enrollment=enrollment,
                    center=enrollment.center,
                    student=enrollment.student,
                    gross_amount=gross,
                    scholarship_amount=money(0),
                    net_amount=gross,
                    paid_amount=money(0),
                    refunded_amount=money(0),
                    status=InvoiceStatus.PAID if gross == 0 else InvoiceStatus.UNPAID,
                )
            return invoice
        except IntegrityError:
            continue
    raise BusinessRuleError('Could not generate an invoice number. Try again.')


def discount_for(scholarship, gross):
    """Calculate the fee reduction. A discount never exceeds the gross fee."""

    gross = money(gross)
    if scholarship.scholarship_type == ScholarshipType.PERCENTAGE:
        if scholarship.value < 0 or scholarship.value > 100:
            raise BusinessRuleError('A percentage scholarship must be between 0 and 100.')
        return money(gross * scholarship.value / Decimal('100'))
    if scholarship.value < 0:
        raise BusinessRuleError('A scholarship amount cannot be negative.')
    if money(scholarship.value) > gross:
        raise BusinessRuleError('A fixed scholarship cannot exceed the course fee.')
    return money(scholarship.value)


def _redistribute_installments(invoice):
    installments = list(invoice.installments.order_by('number'))
    if not installments:
        return
    if any(money(item.paid_amount) > 0 for item in installments):
        raise BusinessRuleError('A scholarship cannot change a plan that already has payments.')
    shares = split_amount(invoice.net_amount, len(installments))
    if money(invoice.net_amount) > 0 and any(share <= 0 for share in shares):
        raise BusinessRuleError('The payable fee is too small to keep this installment plan.')
    for item, share in zip(installments, shares):
        item.amount = share
        item.paid_amount = money(0)
        item.save()


def create_scholarship(data, actor, request=None):
    """Define a scholarship the finance manager can later apply to an enrollment."""

    center = actor.center
    _finance(actor, center, request)
    if data['scholarship_type'] == ScholarshipType.PERCENTAGE and not 0 <= data['value'] <= 100:
        raise BusinessRuleError('A percentage scholarship must be between 0 and 100.')
    if data['value'] < 0:
        raise BusinessRuleError('A scholarship amount cannot be negative.')
    scholarship = Scholarship.objects.create(
        center=center,
        name=data['name'].strip(),
        scholarship_type=data['scholarship_type'],
        value=data['value'],
        description=data.get('description', '') or '',
        is_active=True,
    )
    write_audit(request, 'scholarship.create', f'Created scholarship {scholarship.name}.', user=actor, center=center, entity='scholarship', entity_id=scholarship.id)
    return scholarship


def apply_scholarship(*, scholarship, enrollment, actor, request=None):
    """Reduce one invoice by a scholarship. Refused after any payment is recorded."""

    _finance(actor, enrollment.center, request)
    if scholarship.center_id != enrollment.center_id or not scholarship.is_active:
        raise BusinessRuleError('Choose an active scholarship from this center.')
    if enrollment.status != 'active':
        raise BusinessRuleError('Scholarships apply to active enrollments only.')
    invoice = ensure_invoice(enrollment)
    if money(invoice.paid_amount) > 0 or money(invoice.refunded_amount) > 0:
        raise BusinessRuleError('Apply the scholarship before recording payments or refunds.')
    discount = discount_for(scholarship, invoice.gross_amount)
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        invoice.scholarship_amount = discount
        invoice.net_amount = money(invoice.gross_amount - discount)
        refresh_invoice_status(invoice)
        invoice.save()
        _redistribute_installments(invoice)
        ScholarshipGrant.objects.update_or_create(
            enrollment=enrollment,
            defaults={
                'scholarship': scholarship,
                'invoice': invoice,
                'student': enrollment.student,
                'center': enrollment.center,
                'discount_amount': discount,
                'granted_by': actor,
            },
        )
    write_audit(
        request,
        'scholarship.apply',
        f'Applied {scholarship.name} to {invoice.invoice_number}.',
        user=actor,
        center=enrollment.center,
        entity='invoice',
        entity_id=invoice.id,
    )
    return invoice


def create_installment_plan(*, invoice, installments, actor, request=None):
    """Split the payable fee into 1 to 3 dated installments that sum to the net fee."""

    _finance(actor, invoice.center, request)
    if invoice.installments.exists():
        raise ConflictError('This invoice already has an installment plan.')
    if money(invoice.paid_amount) > 0:
        raise BusinessRuleError('A plan cannot be added after a payment has been recorded.')
    if money(invoice.net_amount) <= 0:
        raise BusinessRuleError('There is nothing left to split into installments.')
    count = len(installments)
    cap = installment_cap(invoice.center)
    if not 1 <= count <= cap:
        raise BusinessRuleError(f'Choose between 1 and {cap} installments.')
    dates = [item['due_date'] for item in installments]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise BusinessRuleError('Due dates must be unique and in ascending order.')
    supplied = [item.get('amount') for item in installments]
    if all(amount is not None for amount in supplied):
        amounts = [money(amount) for amount in supplied]
        if money(sum(amounts, Decimal('0'))) != money(invoice.net_amount):
            raise BusinessRuleError('Installment amounts must add up to the payable fee.')
    else:
        amounts = split_amount(invoice.net_amount, count)
    if money(invoice.net_amount) > 0 and any(amount <= 0 for amount in amounts):
        raise BusinessRuleError('Each installment must be greater than zero.')
    created = []
    for number, (due, amount) in enumerate(zip(dates, amounts), start=1):
        created.append(Installment.objects.create(
            invoice=invoice,
            number=number,
            due_date=due,
            amount=amount,
            paid_amount=money(0),
        ))
    write_audit(request, 'installment.plan', f'Plan created for {invoice.invoice_number}.', user=actor, center=invoice.center, entity='invoice', entity_id=invoice.id)
    return created


def _allocate(invoice, amount):
    """Pour a payment into the oldest installments that are not fully covered."""

    remaining = money(amount)
    for installment in invoice.installments.order_by('number'):
        if remaining <= 0:
            installment.save()
            continue
        room = money(installment.amount - installment.paid_amount)
        if room <= 0:
            installment.save()
            continue
        chunk = room if room <= remaining else remaining
        installment.paid_amount = money(installment.paid_amount + chunk)
        remaining = money(remaining - chunk)
        installment.save()


def record_payment(*, invoice, amount, method, actor, reference='', paid_at=None, request=None):
    """Record a cash or bank receipt and apply it to the installment plan."""

    _finance(actor, invoice.center, request)
    if method not in (PaymentMethod.CASH, PaymentMethod.BANK):
        raise BusinessRuleError('Payment method must be cash or bank.')
    if method == PaymentMethod.BANK and len((reference or '').strip()) < 3:
        raise BusinessRuleError('Bank payments require a reference number.')
    amount = money(amount)
    if amount <= 0:
        raise BusinessRuleError('Payment amount must be greater than zero.')
    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.REFUNDED):
        raise BusinessRuleError('This invoice cannot accept payments.')
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if amount > invoice.outstanding:
            raise BusinessRuleError('Payment exceeds the outstanding balance.')
        payment = Payment.objects.create(
            invoice=invoice,
            center=invoice.center,
            student=invoice.student,
            amount=amount,
            method=method,
            reference=(reference or '').strip(),
            paid_at=paid_at or timezone.now(),
            received_by=actor,
        )
        invoice.paid_amount = money(invoice.paid_amount + amount)
        refresh_invoice_status(invoice)
        invoice.save()
        _allocate(invoice, amount)
    write_audit(
        request,
        'payment.create',
        f'{method} payment of {amount} on {invoice.invoice_number}.',
        user=actor,
        center=invoice.center,
        entity='payment',
        entity_id=payment.id,
    )
    return payment


def request_refund(*, invoice, amount, reason, actor, request=None):
    """Open a refund. Students request their own; finance can request for the center."""

    if actor.role == Role.STUDENT:
        if actor.id != invoice.student_id:
            raise PermissionDenied('Students can request refunds only for their own invoices.')
        assert_same_center(actor, invoice.center, request)
    elif actor.role == Role.FINANCE_MANAGER:
        _finance(actor, invoice.center, request)
    else:
        raise PermissionDenied('Only a student or the finance manager can request a refund.')
    amount = money(amount)
    if amount <= 0:
        raise BusinessRuleError('Refund amount must be greater than zero.')
    if len((reason or '').strip()) < 5:
        raise BusinessRuleError('Explain the refund in at least 5 characters.')
    pending = Refund.objects.filter(invoice=invoice, status=RefundStatus.PENDING).aggregate(total=Sum('amount'))['total'] or 0
    refundable = money(invoice.paid_amount - invoice.refunded_amount - pending)
    if amount > refundable:
        raise BusinessRuleError('Refund exceeds the amount available to return.')
    refund = Refund.objects.create(
        invoice=invoice,
        center=invoice.center,
        student=invoice.student,
        amount=amount,
        reason=reason.strip(),
        status=RefundStatus.PENDING,
        requested_by=actor,
    )
    write_audit(request, 'refund.request', f'Refund requested on {invoice.invoice_number}.', user=actor, center=invoice.center, entity='refund', entity_id=refund.id)
    return refund


def review_refund(*, refund, actor, approve, note='', request=None):
    """Approve or reject a refund. Finance managers cannot take this step."""

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can approve or reject a refund.')
    assert_same_center(actor, refund.center, request)
    assert_operational(actor)
    with transaction.atomic():
        refund = Refund.objects.select_for_update().get(pk=refund.pk)
        if refund.status != RefundStatus.PENDING:
            raise ConflictError('This refund has already been reviewed.')
        if approve:
            invoice = Invoice.objects.select_for_update().get(pk=refund.invoice_id)
            refundable = money(invoice.paid_amount - invoice.refunded_amount)
            if money(refund.amount) > refundable:
                raise BusinessRuleError('The refund is larger than the amount that can be returned.')
            invoice.refunded_amount = money(invoice.refunded_amount + refund.amount)
            refresh_invoice_status(invoice)
            invoice.save()
            refund.status = RefundStatus.APPROVED
        else:
            refund.status = RefundStatus.REJECTED
        refund.reviewed_by = actor
        refund.reviewed_at = timezone.now()
        refund.decision_note = note or ''
        refund.save()
    write_audit(
        request,
        'refund.review',
        f'Refund {refund.id} {refund.status}.',
        user=actor,
        center=refund.center,
        entity='refund',
        entity_id=refund.id,
    )
    return refund


def _sum(queryset, field):
    return money(queryset.aggregate(total=Sum(field))['total'] or 0)


def build_snapshot(center, start=None, end=None):
    """Aggregate the figures shown on dashboards and official reports.

    Expected fees, scholarships, and outstanding amounts follow invoices
    created in the period. Collected cash and refunds follow their own dates,
    so a payment this month is visible even when the invoice is older.
    """

    from apps.centers.models import GlobalSettings

    invoices = Invoice.objects.filter(center=center).exclude(status=InvoiceStatus.CANCELLED)
    payments = Payment.objects.filter(center=center)
    refunds = Refund.objects.filter(center=center, status=RefundStatus.APPROVED)
    if start:
        invoices = invoices.filter(created_at__date__gte=start)
        payments = payments.filter(paid_at__date__gte=start)
        refunds = refunds.filter(reviewed_at__date__gte=start)
    if end:
        invoices = invoices.filter(created_at__date__lte=end)
        payments = payments.filter(paid_at__date__lte=end)
        refunds = refunds.filter(reviewed_at__date__lte=end)
    expected = _sum(invoices, 'net_amount')
    collected = _sum(payments, 'amount')
    outstanding = money(sum((invoice.outstanding for invoice in invoices), Decimal('0')))
    by_method = []
    for method in (PaymentMethod.CASH, PaymentMethod.BANK):
        by_method.append({'method': method, 'total': money_str(_sum(payments.filter(method=method), 'amount'))})
    monthly = {}
    for payment in payments.only('amount', 'paid_at'):
        stamp = timezone.localtime(payment.paid_at)
        key = f'{stamp.year:04d}-{stamp.month:02d}'
        monthly[key] = money(monthly.get(key, 0) + payment.amount)
    courses = []
    grouped = (
        invoices.values('enrollment__course_id', 'enrollment__course__name')
        .annotate(expected=Sum('net_amount'), collected=Sum('paid_amount'), scholarships=Sum('scholarship_amount'))
        .order_by('enrollment__course__name')
    )
    for row in grouped:
        courses.append({
            'course_id': row['enrollment__course_id'],
            'course': row['enrollment__course__name'],
            'expected': money_str(row['expected']),
            'collected': money_str(row['collected']),
            'scholarships': money_str(row['scholarships']),
        })
    students = []
    for invoice in invoices.select_related('student').order_by('student__first_name'):
        students.append({
            'student_id': invoice.student_id,
            'student': invoice.student.full_name,
            'invoice_number': invoice.invoice_number,
            'status': invoice.status,
            'outstanding': money_str(invoice.outstanding),
        })
    return {
        'currency': GlobalSettings.load().currency_label,
        'expected_revenue': money_str(expected),
        'collected_payments': money_str(collected),
        'outstanding_payments': money_str(outstanding),
        'scholarships': money_str(_sum(invoices, 'scholarship_amount')),
        'refunds': money_str(_sum(refunds, 'amount')),
        'payments_by_method': by_method,
        'monthly_revenue': [{'month': key, 'total': money_str(monthly[key])} for key in sorted(monthly)],
        'course_revenue': courses,
        'student_payment_status': students,
    }


def refresh_overdue_installments(center_id=None):
    """Recompute installment status so a due date that passed overnight becomes overdue."""

    queryset = Installment.objects.exclude(status=InstallmentStatus.PAID)
    if center_id:
        queryset = queryset.filter(invoice__center_id=center_id)
    today = timezone.localdate()
    for installment in queryset.filter(due_date__lt=today):
        installment.save()
