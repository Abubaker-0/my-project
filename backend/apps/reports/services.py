"""Dashboards and the official report hand-off.

Finance prepares a snapshot, the center manager sends that snapshot to the
super admin, and the live dashboard reads current rows rather than the
frozen report. Each role receives only the figures they are allowed to see.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.accounts.services import active_contract_for
from apps.attendance.models import AttendanceRecord
from apps.classes.models import ClassSchedule
from apps.common.access import assert_same_center
from apps.common.money import money
from apps.common.audit import write_audit
from apps.common.choices import (
    OPEN_ENROLLMENT,
    AttendanceStatus,
    EnrollmentStatus,
    RefundStatus,
    ReportStatus,
    Role,
)
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.common.money import money_str
from apps.enrollments.models import Enrollment
from apps.finance.models import Installment, Refund
from apps.finance.services import build_snapshot, refresh_overdue_installments
from apps.reports.models import FinancialReport


def _months(count=6):
    today = timezone.localdate()
    year, month = today.year, today.month
    found = []
    for _index in range(count):
        found.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(found))


def _fill_months(rows):
    """Make the chart continuous by adding months that had no payments."""

    indexed = {row['month']: row['total'] for row in rows}
    filled = []
    for year, month in _months(6):
        key = f'{year:04d}-{month:02d}'
        filled.append({'month': key, 'total': indexed.get(key, '0.00')})
    return filled


def _schedule_rows(slots):
    rows = []
    for slot in slots.select_related('course_class__course', 'course_class__teacher', 'classroom')[:12]:
        rows.append({
            'id': slot.id,
            'class_id': slot.course_class_id,
            'class_name': slot.course_class.name,
            'course': slot.course_class.course.name,
            'teacher': slot.course_class.teacher.full_name,
            'classroom': slot.classroom.name,
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
        })
    return rows


def _contract_payload(user):
    contract = active_contract_for(user)
    if contract is None:
        return None
    return {
        'id': contract.id,
        'contract_type': contract.contract_type,
        'start_date': contract.start_date.isoformat(),
        'end_date': contract.end_date.isoformat(),
        'salary_type': contract.salary_type,
        'salary_amount': money_str(contract.salary_amount),
        'payment_method': contract.payment_method,
        'status': contract.status,
    }


def build_dashboard(user):
    """Return the KPI payload for the signed-in role. Queries stay inside the user's center."""

    from apps.centers.models import Center
    from apps.courses.models import Course
    from apps.classes.models import CourseClass
    from apps.finance.models import Payment

    alerts = []
    if user.role == Role.SUPER_ADMIN:
        centers = Center.objects.filter(is_deleted=False)
        refresh_overdue_installments()
    else:
        centers = Center.objects.filter(pk=user.center_id)
        refresh_overdue_installments(user.center_id)
        if not user.center_id or not user.center.is_active:
            alerts.append({'code': 'center_inactive', 'count': 1})

    center_ids = list(centers.values_list('id', flat=True))
    students = User.objects.filter(center_id__in=center_ids, role=Role.STUDENT, is_active=True)
    teachers = User.objects.filter(center_id__in=center_ids, role=Role.TEACHER, is_active=True)
    if user.role == Role.TEACHER:
        courses = Course.objects.filter(is_deleted=False, center_id__in=center_ids).filter(
            Q(teacher=user) | Q(classes__teacher=user)
        ).distinct()
        classes = CourseClass.objects.filter(teacher=user, is_deleted=False)
    elif user.role == Role.STUDENT:
        courses = Course.objects.filter(
            enrollments__student=user,
            enrollments__status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        ).distinct()
        classes = CourseClass.objects.filter(enrollments__student=user, enrollments__status=EnrollmentStatus.ACTIVE)
    else:
        courses = Course.objects.filter(center_id__in=center_ids, is_deleted=False)
        classes = CourseClass.objects.filter(center_id__in=center_ids, is_deleted=False)

    payments = Payment.objects.filter(center_id__in=center_ids)
    snapshot_collected = money_str(sum((payment.amount for payment in payments), start=0))
    attendance = AttendanceRecord.objects.filter(session__center_id__in=center_ids)
    if user.role == Role.TEACHER:
        attendance = attendance.filter(session__course_class__teacher=user)
    if user.role == Role.STUDENT:
        attendance = attendance.filter(student=user)
    present = attendance.filter(status=AttendanceStatus.PRESENT).count()
    absent = attendance.filter(status=AttendanceStatus.ABSENT).count()
    enrollments = Enrollment.objects.filter(center_id__in=center_ids, status__in=OPEN_ENROLLMENT)
    if user.role == Role.STUDENT:
        enrollments = enrollments.filter(student=user)
    pending_refunds = Refund.objects.filter(center_id__in=center_ids, status=RefundStatus.PENDING).count()
    overdue = Installment.objects.filter(invoice__center_id__in=center_ids, status='overdue').count()
    if pending_refunds and user.role in (Role.CENTER_MANAGER, Role.FINANCE_MANAGER, Role.SUPER_ADMIN):
        alerts.append({'code': 'pending_refunds', 'count': pending_refunds})
    if overdue and user.role in (Role.FINANCE_MANAGER, Role.CENTER_MANAGER, Role.SUPER_ADMIN):
        alerts.append({'code': 'overdue_installments', 'count': overdue})

    monthly_map = {}
    start_month = _months(6)[0]
    start_date = timezone.datetime(start_month[0], start_month[1], 1, tzinfo=timezone.get_current_timezone())
    for payment in payments.filter(paid_at__gte=start_date).only('amount', 'paid_at'):
        stamp = timezone.localtime(payment.paid_at)
        key = f'{stamp.year:04d}-{stamp.month:02d}'
        monthly_map[key] = monthly_map.get(key, 0) + payment.amount
    monthly = _fill_months([{'month': key, 'total': money_str(value)} for key, value in monthly_map.items()])
    methods = []
    for method in ('cash', 'bank'):
        total = sum((payment.amount for payment in payments.filter(method=method)), start=0)
        methods.append({'method': method, 'total': money_str(total)})

    today = timezone.localdate()
    slots = ClassSchedule.objects.filter(
        day_of_week=today.weekday(),
        course_class__is_deleted=False,
        course_class__course__start_date__lte=today,
        course_class__course__end_date__gte=today,
        course_class__center_id__in=center_ids,
    )
    if user.role == Role.TEACHER:
        slots = slots.filter(course_class__teacher=user)
    if user.role == Role.STUDENT:
        slots = slots.filter(course_class__enrollments__student=user, course_class__enrollments__status=EnrollmentStatus.ACTIVE)

    center_rows = []
    if user.role == Role.SUPER_ADMIN:
        for center in centers.order_by('name'):
            snap = build_snapshot(center)
            center_rows.append({
                'id': center.id,
                'name': center.name,
                'code': center.code,
                'is_active': center.is_active,
                'students': User.objects.filter(center=center, role=Role.STUDENT, is_active=True).count(),
                'teachers': User.objects.filter(center=center, role=Role.TEACHER, is_active=True).count(),
                'courses': Course.objects.filter(center=center, is_deleted=False).count(),
                'expected': snap['expected_revenue'],
                'collected': snap['collected_payments'],
                'outstanding': snap['outstanding_payments'],
            })

    outstanding = '0.00'
    if center_ids and user.role != Role.STUDENT:
        outstanding = money_str(sum(
            (float(build_snapshot(center)['outstanding_payments']) for center in centers),
            start=0,
        ))
    elif user.role == Role.STUDENT and user.center_id:
        from apps.finance.models import Invoice
        outstanding = money_str(sum(
            (invoice.outstanding for invoice in Invoice.objects.filter(student=user)),
            start=0,
        ))

    kpis = {
        Role.SUPER_ADMIN: [
            {'key': 'centers', 'value': centers.count()},
            {'key': 'students', 'value': students.count()},
            {'key': 'teachers', 'value': teachers.count()},
            {'key': 'courses', 'value': courses.count()},
            {'key': 'collected', 'value': snapshot_collected},
        ],
        Role.CENTER_MANAGER: [
            {'key': 'students', 'value': students.count()},
            {'key': 'teachers', 'value': teachers.count()},
            {'key': 'courses', 'value': courses.count()},
            {'key': 'classes', 'value': classes.count()},
            {'key': 'outstanding', 'value': outstanding},
            {'key': 'refunds', 'value': pending_refunds},
        ],
        Role.FINANCE_MANAGER: [
            {'key': 'collected', 'value': snapshot_collected},
            {'key': 'outstanding', 'value': outstanding},
            {'key': 'overdue', 'value': overdue},
            {'key': 'refunds', 'value': pending_refunds},
        ],
        Role.TEACHER: [
            {'key': 'courses', 'value': courses.count()},
            {'key': 'classes', 'value': classes.count()},
            {'key': 'present', 'value': present},
            {'key': 'absent', 'value': absent},
        ],
        Role.STUDENT: [
            {'key': 'courses', 'value': courses.count()},
            {'key': 'present', 'value': present},
            {'key': 'absent', 'value': absent},
            {'key': 'outstanding', 'value': outstanding},
        ],
    }
    contract = _contract_payload(user) if user.role in (Role.CENTER_MANAGER, Role.FINANCE_MANAGER, Role.TEACHER) else None
    if user.role in (Role.TEACHER, Role.FINANCE_MANAGER, Role.CENTER_MANAGER) and contract is None:
        alerts.append({'code': 'contract_inactive', 'count': 1})
    return {
        'role': user.role,
        'kpis': kpis.get(user.role, []),
        'monthly_revenue': monthly,
        'payment_methods': methods,
        'attendance': {'present': present, 'absent': absent},
        'enrollment': {
            'active': enrollments.filter(status=EnrollmentStatus.ACTIVE).count(),
            'pending': enrollments.filter(status=EnrollmentStatus.PENDING).count(),
        },
        'refunds_pending': pending_refunds,
        'overdue_installments': overdue,
        'today_schedule': _schedule_rows(slots),
        'center_rows': center_rows,
        'contract': contract,
        'alerts': alerts,
        'currency': build_snapshot(centers.first()).get('currency', 'AFN') if centers.exists() else 'AFN',
    }


def create_financial_report(*, center, title, start, end, actor, request=None):
    """Freeze a finance snapshot. Only the center's finance manager can prepare it."""

    from apps.common.permissions_catalog import has_permission

    if actor.role != Role.FINANCE_MANAGER:
        raise PermissionDenied('Only the finance manager can prepare a financial report.')
    if not has_permission(actor, 'reports.prepare', center):
        raise PermissionDenied('Report preparation is restricted for this center.')
    assert_same_center(actor, center, request)
    from apps.accounts.services import assert_operational
    assert_operational(actor)
    if end < start:
        raise BusinessRuleError('The report end date cannot be before the start date.')
    report = FinancialReport.objects.create(
        center=center,
        title=(title or f'{center.name} {start.isoformat()} – {end.isoformat()}').strip(),
        period_start=start,
        period_end=end,
        status=ReportStatus.DRAFT,
        prepared_by=actor,
        snapshot=build_snapshot(center, start, end),
    )
    write_audit(request, 'report.create', f'Report {report.id} drafted.', user=actor, center=center, entity='report', entity_id=report.id)
    return report


def submit_report(report, actor, request=None):
    """Hand a draft report to the center manager."""

    if actor.role != Role.FINANCE_MANAGER:
        raise PermissionDenied('Only the finance manager can submit a report.')
    assert_same_center(actor, report.center, request)
    if report.status != ReportStatus.DRAFT:
        raise ConflictError('Only a draft report can be submitted.')
    report.status = ReportStatus.SUBMITTED_TO_MANAGER
    report.submitted_at = timezone.now()
    report.save(update_fields=['status', 'submitted_at', 'updated_at'])
    write_audit(request, 'report.submit', f'Report {report.id} submitted.', user=actor, center=report.center, entity='report', entity_id=report.id)
    return report


def send_report(report, actor, request=None):
    """Center manager sends a submitted report to the super admin."""

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can send a report to the super admin.')
    assert_same_center(actor, report.center, request)
    from apps.accounts.services import assert_operational
    assert_operational(actor)
    if report.status != ReportStatus.SUBMITTED_TO_MANAGER:
        raise BusinessRuleError('The finance manager must submit the report before it can be sent.')
    report.status = ReportStatus.SENT_TO_SUPER_ADMIN
    report.sent_by = actor
    report.sent_at = timezone.now()
    report.save(update_fields=['status', 'sent_by', 'sent_at', 'updated_at'])
    write_audit(request, 'report.send', f'Report {report.id} sent to super admin.', user=actor, center=report.center, entity='report', entity_id=report.id)
    return report


def return_report(report, actor, note, request=None):
    """Send a submitted report back. The frozen snapshot is not edited."""

    if actor.role != Role.CENTER_MANAGER:
        raise PermissionDenied('Only the center manager can return a report.')
    assert_same_center(actor, report.center, request)
    from apps.accounts.services import assert_operational
    assert_operational(actor)
    if report.status != ReportStatus.SUBMITTED_TO_MANAGER:
        raise BusinessRuleError('Only a submitted report can be returned.')
    if len((note or '').strip()) < 5:
        raise BusinessRuleError('Explain why the report is being returned.')
    report.status = ReportStatus.RETURNED
    report.return_note = note.strip()
    report.returned_by = actor
    report.returned_at = timezone.now()
    report.save(update_fields=['status', 'return_note', 'returned_by', 'returned_at', 'updated_at'])
    from apps.common.notifications import notify
    notify(
        report.prepared_by,
        'report',
        'Report returned',
        f'{report.title} was returned. Create a new revision; the sent snapshot is never edited.',
        dedupe_key=f'report-return:{report.id}',
    )
    write_audit(request, 'report.return', f'Report {report.id} returned.', user=actor, center=report.center, entity='report', entity_id=report.id)
    return report


def revise_report(report, actor, request=None):
    """Create a linked draft from a returned report. The previous snapshot stays."""

    from apps.common.permissions_catalog import has_permission

    if actor.role != Role.FINANCE_MANAGER:
        raise PermissionDenied('Only the finance manager can revise a report.')
    if not has_permission(actor, 'reports.prepare', report.center):
        raise PermissionDenied('Report preparation is restricted for this center.')
    assert_same_center(actor, report.center, request)
    from apps.accounts.services import assert_operational
    assert_operational(actor)
    if report.status != ReportStatus.RETURNED:
        raise BusinessRuleError('A revision can be created only from a returned report.')
    if report.revisions.filter(status=ReportStatus.DRAFT).exists():
        raise ConflictError('A draft revision already exists for this report.')
    revision = FinancialReport.objects.create(
        center=report.center,
        title=report.title,
        period_start=report.period_start,
        period_end=report.period_end,
        status=ReportStatus.DRAFT,
        prepared_by=actor,
        revision=report.revision + 1,
        previous=report,
        snapshot=build_snapshot(report.center, report.period_start, report.period_end),
    )
    write_audit(request, 'report.revise', f'Report {revision.id} revises {report.id}.', user=actor, center=report.center, entity='report', entity_id=revision.id)
    return revision


def integrity_report():
    """Read-only checks. This function never changes rows."""

    from apps.accounts.models import Contract
    from apps.centers.models import Center
    from apps.common.choices import OPEN_ENROLLMENT
    from apps.enrollments.models import Enrollment
    from apps.finance.models import Invoice

    issues = []
    for center in Center.objects.filter(is_deleted=False, is_active=True):
        if center.get_active_manager() is None:
            issues.append({'code': 'active_center_without_manager', 'center': center.code})
    for invoice in Invoice.objects.all().iterator():
        if money(invoice.paid_amount) > money(invoice.net_amount):
            issues.append({'code': 'paid_above_net', 'invoice': invoice.invoice_number})
        planned = list(invoice.installments.all())
        if planned and money(sum((item.amount for item in planned), Decimal('0'))) != money(invoice.net_amount):
            issues.append({'code': 'installment_sum_mismatch', 'invoice': invoice.invoice_number})
    open_pairs = (
        Enrollment.objects.filter(status__in=OPEN_ENROLLMENT)
        .values('student_id', 'course_id')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    for pair in open_pairs:
        issues.append({'code': 'duplicate_open_enrollment', 'student': pair['student_id'], 'course': pair['course_id']})
    expired_locks = Contract.objects.filter(status='active', end_date__lt=timezone.localdate()).count()
    if expired_locks:
        issues.append({'code': 'expired_contract_still_active', 'count': expired_locks})
    return issues
