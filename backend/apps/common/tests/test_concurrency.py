"""MySQL races. SQLite skips these because it does not prove row locks.

Run: TEST_DB=mysql python manage.py test apps.common.tests.test_concurrency
"""

import threading
from datetime import time

from django.db import connection
from django.test import TransactionTestCase

from apps.accounts.models import Contract, User
from apps.accounts.services import create_account, create_contract
from apps.centers.services import assign_manager, create_center, set_center_active
from apps.classes.models import ClassSchedule
from apps.classes.services import add_schedule
from apps.common.choices import OPEN_ENROLLMENT, Role
from apps.common.exceptions import BusinessRuleError, ConflictError
from apps.common.tests.test_business_rules import contract, person
from apps.enrollments.models import Enrollment, WaitlistEntry
from apps.enrollments.services import enroll, join_waitlist, promote_waitlist
from apps.finance.models import Invoice, Payment, Refund
from apps.finance.services import record_payment, request_refund, review_refund
from apps.common.choices import EnrollmentSource


class MySQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor != 'mysql':
            self.skipTest('MySQL is required for these lock tests. SQLite is not accepted as proof.')
        self.admin = User.objects.create_superuser(
            'superadmin', 'superadmin@tuition.local', 'Admin@12345',
            first_name='System', last_name='Admin', phone='+93700000000', gender='male',
        )
        self.center = create_center({'name': 'Kabul Star', 'code': 'KBL', 'city': 'Kabul'}, self.admin)
        self.manager = create_account(person('manager.kabul', Role.CENTER_MANAGER), self.admin)
        assign_manager(center=self.center, manager=self.manager, contract_data=contract(), actor=self.admin)
        set_center_active(self.center, True, self.admin)
        self.manager = User.objects.get(pk=self.manager.pk)
        self.finance = create_account(person('finance.kabul', Role.FINANCE_MANAGER, contract=contract()), self.manager)
        self.teacher = create_account(person('teacher.zahra', Role.TEACHER, contract=contract()), self.manager)
        self.student = create_account(person('student.ali', Role.STUDENT), self.manager)
        self.student_two = create_account(person('student.maryam', Role.STUDENT), self.manager)

    def _race(self, left, right):
        barrier = threading.Barrier(2)
        box = {}

        def wrap(name, fn):
            try:
                box[name] = fn(barrier)
            except Exception as exc:
                box[name] = exc
            finally:
                connection.close()

        threads = [threading.Thread(target=wrap, args=('left', left)), threading.Thread(target=wrap, args=('right', right))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        return box

    def _course(self, capacity=1):
        from apps.classes.services import create_classroom
        from apps.courses.services import create_course
        from datetime import date

        room = create_classroom(self.center, f'Room {capacity}-{User.objects.count()}', 30, self.manager)
        course = create_course({
            'name': f'Course {User.objects.count()}',
            'description': 'Concurrency course.',
            'teacher': self.teacher,
            'duration_hours': 40,
            'start_date': date(2026, 9, 1),
            'end_date': date(2026, 12, 31),
            'fee': '100.00',
            'capacity': capacity,
            'section_name': 'Section A',
            'schedules': [{
                'day_of_week': 0,
                'start_time': time(8, 0),
                'end_time': time(9, 0),
                'classroom': room,
            }],
        }, self.manager)
        return course

    def test_one_seat_accepts_one_enrollment(self):
        course = self._course(1)
        section = course.classes.first()

        def attempt(student):
            def run(barrier):
                barrier.wait(5)
                return enroll(
                    student=student, course=course, course_class=section,
                    actor=self.manager, source=EnrollmentSource.MANUAL,
                )
            return run

        box = self._race(attempt(self.student), attempt(self.student_two))
        self.assertEqual(Enrollment.objects.filter(course=course, status__in=OPEN_ENROLLMENT).count(), 1)
        self.assertEqual(sum(isinstance(value, Enrollment) for value in box.values()), 1)
        self.assertTrue(any(isinstance(value, ConflictError) for value in box.values()))

    def test_duplicate_open_enrollment_is_rejected(self):
        course = self._course(5)
        section = course.classes.first()

        def run(barrier):
            barrier.wait(5)
            return enroll(
                student=self.student, course=course, course_class=section,
                actor=self.manager, source=EnrollmentSource.MANUAL,
            )

        box = self._race(run, run)
        self.assertEqual(Enrollment.objects.filter(student=self.student, course=course, status__in=OPEN_ENROLLMENT).count(), 1)
        self.assertTrue(any(isinstance(value, ConflictError) for value in box.values()))

    def test_one_active_staff_contract(self):
        extra = User.objects.create_user(
            'teacher.extra', 'teacher.extra@tuition.local', 'Staff@12345',
            first_name='Extra', last_name='Teacher', phone='+93700000000', gender='male',
            role=Role.TEACHER, center=self.center,
        )

        def run(barrier):
            barrier.wait(5)
            return create_contract(extra, self.center, contract(), self.manager)

        box = self._race(run, run)
        self.assertEqual(Contract.objects.filter(user=extra, status='active').count(), 1)
        self.assertTrue(any(isinstance(value, ConflictError) for value in box.values()))

    def test_manager_replacement_leaves_one_lock(self):
        first = create_account(person('manager.one', Role.CENTER_MANAGER), self.admin)
        second = create_account(person('manager.two', Role.CENTER_MANAGER), self.admin)

        def attempt(manager):
            def run(barrier):
                barrier.wait(5)
                return assign_manager(
                    center=self.center, manager=manager, contract_data=contract(),
                    actor=self.admin, replace=True,
                )
            return run

        self._race(attempt(first), attempt(second))
        self.assertEqual(Contract.objects.filter(active_manager_lock=self.center.id, status='active').count(), 1)

    def test_overlapping_schedules_cannot_both_commit(self):
        course = self._course(5)
        first = course.classes.first()
        from apps.classes.services import create_class
        from apps.classes.models import Classroom
        room = Classroom.objects.filter(center=self.center).first()
        second = create_class(
            course=course, name='Section B', teacher=self.teacher,
            schedules=[{'day_of_week': 2, 'start_time': time(8, 0), 'end_time': time(9, 0), 'classroom': room}],
            actor=self.manager,
        )

        def attempt(section):
            def run(barrier):
                barrier.wait(5)
                return add_schedule(section, {
                    'day_of_week': 4, 'start_time': time(14, 0), 'end_time': time(15, 0), 'classroom': room,
                }, self.manager)
            return run

        box = self._race(attempt(first), attempt(second))
        self.assertEqual(ClassSchedule.objects.filter(course_class__teacher=self.teacher, day_of_week=4).count(), 1)
        self.assertTrue(any(isinstance(value, ConflictError) for value in box.values()))

    def test_two_payments_cannot_exceed_the_balance(self):
        course = self._course(2)
        enrollment = enroll(
            student=self.student, course=course, course_class=course.classes.first(),
            actor=self.manager, source=EnrollmentSource.MANUAL,
        )
        invoice = Invoice.objects.get(enrollment=enrollment)

        def attempt(key):
            def run(barrier):
                barrier.wait(5)
                return record_payment(
                    invoice=invoice, amount='80.00', method='cash', actor=self.finance, idempotency_key=key,
                )
            return run

        box = self._race(attempt('pay-left'), attempt('pay-right'))
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, invoice.payments.get().amount)
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertTrue(any(isinstance(value, BusinessRuleError) for value in box.values()))

    def test_two_approvals_refund_the_money_once(self):
        course = self._course(2)
        enrollment = enroll(
            student=self.student, course=course, course_class=course.classes.first(),
            actor=self.manager, source=EnrollmentSource.MANUAL,
        )
        invoice = Invoice.objects.get(enrollment=enrollment)
        record_payment(invoice=invoice, amount='100.00', method='cash', actor=self.finance, idempotency_key='seed-pay')
        refund = request_refund(invoice=invoice, amount='60.00', reason='Return part of the fee.', actor=self.finance)

        def run(barrier):
            barrier.wait(5)
            return review_refund(refund=refund, actor=self.manager, approve=True, note='Approved once.')

        box = self._race(run, run)
        invoice.refresh_from_db()
        refund.refresh_from_db()
        self.assertEqual(invoice.refunded_amount, refund.amount)
        self.assertEqual(Refund.objects.filter(invoice=invoice, status='approved').count(), 1)
        self.assertTrue(any(isinstance(value, ConflictError) for value in box.values()))

    def test_two_promotions_take_one_seat(self):
        course = self._course(1)
        section = course.classes.first()
        first = join_waitlist(student=self.student, course=course, course_class=section, actor=self.student)
        second = join_waitlist(student=self.student_two, course=course, course_class=section, actor=self.student_two)

        def attempt(entry):
            def run(barrier):
                barrier.wait(5)
                return promote_waitlist(entry, self.manager)
            return run

        self._race(attempt(first), attempt(second))
        self.assertEqual(Enrollment.objects.filter(course=course, status__in=OPEN_ENROLLMENT).count(), 1)
        self.assertEqual(WaitlistEntry.objects.filter(course=course, status=WaitlistEntry.WAITING).count(), 1)

    def test_identical_idempotency_keys_create_one_payment(self):
        course = self._course(2)
        enrollment = enroll(
            student=self.student, course=course, course_class=course.classes.first(),
            actor=self.manager, source=EnrollmentSource.MANUAL,
        )
        invoice = Invoice.objects.get(enrollment=enrollment)

        def run(barrier):
            barrier.wait(5)
            return record_payment(
                invoice=invoice, amount='25.00', method='cash', actor=self.finance, idempotency_key='same-key',
            )

        box = self._race(run, run)
        invoice.refresh_from_db()
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(invoice.paid_amount, Payment.objects.get(invoice=invoice).amount)
        self.assertTrue(all(isinstance(value, Payment) for value in box.values()))
        self.assertEqual({value.id for value in box.values()}, {Payment.objects.get(invoice=invoice).id})

    def test_same_key_with_different_payloads_keeps_one_amount(self):
        course = self._course(2)
        enrollment = enroll(
            student=self.student, course=course, course_class=course.classes.first(),
            actor=self.manager, source=EnrollmentSource.MANUAL,
        )
        invoice = Invoice.objects.get(enrollment=enrollment)

        def attempt(amount):
            def run(barrier):
                barrier.wait(5)
                return record_payment(
                    invoice=invoice, amount=amount, method='cash', actor=self.finance, idempotency_key='shared-key',
                )
            return run

        box = self._race(attempt('10.00'), attempt('15.00'))
        invoice.refresh_from_db()
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(invoice.paid_amount, Payment.objects.get(invoice=invoice).amount)
        self.assertTrue(any(isinstance(value, ConflictError) for value in box.values()))
