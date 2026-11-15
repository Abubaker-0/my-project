"""Load two demo centers with people, classes, money, and attendance.

The command is safe to run twice: if the Kabul center already exists it
leaves the database alone. It uses the same services as the API, so the
seeded records obey capacity, contract, and payment rules.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import create_account
from apps.attendance.services import mark_attendance
from apps.centers.models import Center
from apps.centers.services import assign_manager, create_center, set_center_active
from apps.classes.services import create_classroom
from apps.common.choices import EnrollmentSource, Gender, Role
from apps.courses.services import create_course
from apps.enrollments.models import Enrollment
from apps.enrollments.services import enroll
from apps.finance.models import Invoice
from apps.finance.services import (
    apply_scholarship,
    create_installment_plan,
    create_scholarship,
    record_payment,
    request_refund,
)
from apps.reports.services import create_financial_report, send_report, submit_report


def staff_contract(kind='yearly'):
    """An active contract window measured from today."""

    start = timezone.localdate() - timedelta(days=40)
    days = 365 if kind == 'yearly' else 182
    return {
        'contract_type': kind,
        'start_date': start,
        'end_date': start + timedelta(days=days),
        'salary_type': 'monthly',
        'salary_amount': Decimal('35000.00'),
        'payment_method': 'bank',
    }


class Command(BaseCommand):
    help = 'Seed two tuition centers and sample academic and finance records.'

    def handle(self, *args, **options):
        if Center.objects.filter(code='KBL').exists():
            self.stdout.write(self.style.WARNING('Seed data already exists.'))
            return
        admin = User.objects.filter(role=Role.SUPER_ADMIN).first()
        if admin is None:
            admin = User.objects.create_superuser(
                'superadmin', 'superadmin@tuition.local', 'Admin@12345',
                first_name='System', last_name='Administrator', phone='+93700000000', gender=Gender.MALE,
            )
        kabul = self._center(admin, 'Kabul Star Tuition', 'KBL', 'Kabul', 'manager.kabul', 'Ahmad', 'Shah', Gender.MALE)
        herat = self._center(admin, 'Herat Knowledge Academy', 'HRT', 'Herat', 'manager.herat', 'Laila', 'Hotak', Gender.FEMALE)
        self._kabul_operations(kabul)
        self._herat_operations(herat)
        self.stdout.write(self.style.SUCCESS('Seed data created. See README for demo logins.'))

    def _center(self, admin, name, code, city, username, first, last, gender):
        center = create_center({'name': name, 'code': code, 'city': city, 'phone': '+93200000000'}, admin)
        manager = self._user(admin, username, first, last, gender, Role.CENTER_MANAGER, 'Manager@12345')
        assign_manager(center=center, manager=manager, contract_data=staff_contract(), actor=admin)
        set_center_active(center, True, admin)
        return center

    def _user(self, actor, username, first, last, gender, role, password, contract=None):
        return create_account({
            'username': username,
            'email': f'{username}@tuition.local',
            'password': password,
            'first_name': first,
            'last_name': last,
            'phone': '+93700011223',
            'gender': gender,
            'role': role,
            'contract': contract,
        }, actor)

    def _kabul_operations(self, center):
        manager = User.objects.get(username='manager.kabul')
        finance = self._user(manager, 'finance.kabul', 'Fatima', 'Noori', Gender.FEMALE, Role.FINANCE_MANAGER, 'Finance@12345', staff_contract())
        zahra = self._user(manager, 'teacher.zahra', 'Zahra', 'Ahmadi', Gender.FEMALE, Role.TEACHER, 'Teacher@12345', staff_contract())
        karim = self._user(manager, 'teacher.karim', 'Karim', 'Sadat', Gender.MALE, Role.TEACHER, 'Teacher@12345', staff_contract('six_months'))
        karim.contracts.filter(status='active').update(salary_type='hourly', salary_amount=Decimal('500.00'), payment_method='cash')
        ali = self._user(manager, 'student.ali', 'Ali', 'Rahimi', Gender.MALE, Role.STUDENT, 'Student@12345')
        maryam = self._user(manager, 'student.maryam', 'Maryam', 'Karimi', Gender.FEMALE, Role.STUDENT, 'Student@12345')
        omar = self._user(manager, 'student.omar', 'Omar', 'Farhadi', Gender.MALE, Role.STUDENT, 'Student@12345')
        room_a = create_classroom(center, 'Room A', 30, manager)
        room_b = create_classroom(center, 'Room B', 24, manager)
        start = timezone.localdate() - timedelta(days=50)
        end = timezone.localdate() + timedelta(days=100)
        math = create_course(self._course_payload('Mathematics Grade 10', 'MATH10', zahra, '3200.00', 20, room_a, 0, '08:00', '09:30', start, end), manager)
        english = create_course(self._course_payload('English Intermediate', 'ENG2', karim, '2500.00', 16, room_b, 0, '12:00', '13:30', start, end), manager)
        physics = create_course(self._course_payload('Physics Foundations', 'PHY1', zahra, '2800.00', 12, room_a, 1, '10:00', '11:30', start, end), manager)
        math_class = math.classes.get(is_deleted=False)
        english_class = english.classes.get(is_deleted=False)
        physics_class = physics.classes.get(is_deleted=False)
        ali_math = enroll(student=ali, course=math, course_class=math_class, actor=manager, source=EnrollmentSource.MANUAL)
        enroll(student=ali, course=english, course_class=english_class, actor=ali, source=EnrollmentSource.SELF)
        maryam_math = enroll(student=maryam, course=math, course_class=math_class, actor=manager, source=EnrollmentSource.MANUAL)
        enroll(student=omar, course=physics, course_class=physics_class, actor=omar, source=EnrollmentSource.SELF)
        merit = create_scholarship({
            'name': 'Merit 20%',
            'scholarship_type': 'percentage',
            'value': Decimal('20'),
            'description': 'Awarded for strong entrance results.',
        }, finance)
        apply_scholarship(scholarship=merit, enrollment=maryam_math, actor=finance)
        invoice = Invoice.objects.get(enrollment=ali_math)
        create_installment_plan(invoice=invoice, installments=[
            {'due_date': start + timedelta(days=15), 'amount': Decimal('1066.67')},
            {'due_date': start + timedelta(days=45), 'amount': Decimal('1066.67')},
            {'due_date': start + timedelta(days=75), 'amount': Decimal('1066.66')},
        ], actor=finance)
        record_payment(invoice=invoice, amount=Decimal('1600.00'), method='bank', actor=finance, reference='BANK-10021', paid_at=self._months_ago(2))
        record_payment(invoice=Invoice.objects.get(enrollment=Enrollment.objects.get(student=ali, course=english)), amount=Decimal('900.00'), method='cash', actor=finance, paid_at=self._months_ago(1))
        physics_invoice = Invoice.objects.get(enrollment__student=omar, enrollment__course=physics)
        record_payment(invoice=physics_invoice, amount=Decimal('400.00'), method='cash', actor=finance, paid_at=self._months_ago(0))
        physics_invoice.refresh_from_db()
        request_refund(invoice=physics_invoice, amount=Decimal('100.00'), reason='Student requested a partial refund.', actor=finance)
        self._attendance(math_class, zahra, [ali, maryam])
        report = create_financial_report(
            center=center,
            title='Kabul term finance report',
            start=start,
            end=timezone.localdate(),
            actor=finance,
        )
        submit_report(report, finance)
        send_report(report, manager)

    def _herat_operations(self, center):
        manager = User.objects.get(username='manager.herat')
        finance = self._user(manager, 'finance.herat', 'Yusuf', 'Amini', Gender.MALE, Role.FINANCE_MANAGER, 'Finance@12345', staff_contract())
        teacher = self._user(manager, 'teacher.herat', 'Nasrin', 'Barak', Gender.FEMALE, Role.TEACHER, 'Teacher@12345', staff_contract())
        student = self._user(manager, 'student.herat', 'Hassan', 'Safi', Gender.MALE, Role.STUDENT, 'Student@12345')
        room = create_classroom(center, 'Room 1', 20, manager)
        start = timezone.localdate() - timedelta(days=30)
        end = timezone.localdate() + timedelta(days=80)
        course = create_course(self._course_payload('Dari Literature', 'DARI1', teacher, '1800.00', 14, room, 2, '09:00', '10:30', start, end), manager)
        enrollment = enroll(student=student, course=course, course_class=course.classes.get(), actor=student, source=EnrollmentSource.SELF)
        record_payment(invoice=Invoice.objects.get(enrollment=enrollment), amount=Decimal('600.00'), method='bank', actor=finance, reference='HRT-2001', paid_at=self._months_ago(0))

    def _course_payload(self, name, code, teacher, fee, capacity, room, day, start_time, end_time, start, end):
        return {
            'name': name,
            'code': code,
            'description': f'{name} is taught at this center with weekly live classes.',
            'teacher': teacher,
            'duration_hours': 48,
            'start_date': start,
            'end_date': end,
            'fee': Decimal(fee),
            'capacity': capacity,
            'section_name': 'Section A',
            'schedules': [{
                'day_of_week': day,
                'start_time': datetime.strptime(start_time, '%H:%M').time(),
                'end_time': datetime.strptime(end_time, '%H:%M').time(),
                'classroom': room,
            }],
        }

    def _months_ago(self, months):
        today = timezone.localdate()
        month = today.month - months
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        day = min(today.day, 28)
        return timezone.make_aware(datetime(year, month, day, 10, 0))

    def _attendance(self, course_class, teacher, students):
        day = timezone.localdate()
        while day.weekday() != course_class.schedules.first().day_of_week or day < course_class.course.start_date:
            day -= timedelta(days=1)
            if day < course_class.course.start_date - timedelta(days=1):
                return
        if day < course_class.course.start_date or day > timezone.localdate():
            return
        mark_attendance(
            course_class=course_class,
            day=day,
            records=[{'student_id': students[0].id, 'status': 'present'}, {'student_id': students[1].id, 'status': 'absent'}],
            actor=teacher,
        )
