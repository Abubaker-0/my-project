"""API tests for the rules the product must not break.

These tests go through HTTP so role checks, center isolation, and validation
all run together. The database is SQLite during tests; the same service code
runs on MySQL in development.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_account
from apps.centers.services import assign_manager, create_center, set_center_active
from apps.common.choices import Gender, Role
from apps.common.exceptions import BusinessRuleError
from apps.finance.services import create_installment_plan


def contract(kind='yearly'):
    """A contract window that is active today and matches the length rule."""

    start = timezone.localdate() - timedelta(days=30)
    days = 365 if kind == 'yearly' else 182
    return {
        'contract_type': kind,
        'start_date': start,
        'end_date': start + timedelta(days=days),
        'salary_type': 'monthly',
        'salary_amount': '25000.00',
        'payment_method': 'bank',
    }


def person(username, role, **extra):
    payload = {
        'username': username,
        'email': f'{username}@tuition.local',
        'password': 'Staff@12345',
        'first_name': username.split('.')[0].title(),
        'last_name': 'Test',
        'phone': '+93700000000',
        'gender': Gender.MALE,
        'role': role,
    }
    payload.update(extra)
    return payload


class BusinessRuleTests(APITestCase):
    """Critical center, enrollment, attendance, and finance rules."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            'superadmin', 'superadmin@tuition.local', 'Admin@12345',
            first_name='System', last_name='Admin', phone='+93700000000', gender=Gender.MALE,
        )
        self.center = create_center({'name': 'Kabul Star', 'code': 'KBL', 'city': 'Kabul'}, self.admin)
        self.other = create_center({'name': 'Herat Academy', 'code': 'HRT', 'city': 'Herat'}, self.admin)
        self.manager = create_account(person('manager.kabul', Role.CENTER_MANAGER, gender=Gender.MALE), self.admin)
        assign_manager(center=self.center, manager=self.manager, contract_data=contract(), actor=self.admin)
        set_center_active(self.center, True, self.admin)
        self.manager = User.objects.get(pk=self.manager.pk)
        self.other_manager = create_account(person('manager.herat', Role.CENTER_MANAGER, gender=Gender.FEMALE), self.admin)
        assign_manager(center=self.other, manager=self.other_manager, contract_data=contract(), actor=self.admin)
        set_center_active(self.other, True, self.admin)
        self.other_manager = User.objects.get(pk=self.other_manager.pk)
        self.finance = create_account(
            person('finance.kabul', Role.FINANCE_MANAGER, gender=Gender.FEMALE, contract=contract()),
            self.manager,
        )
        self.teacher = create_account(
            person('teacher.zahra', Role.TEACHER, gender=Gender.FEMALE, contract=contract()),
            self.manager,
        )
        self.teacher_two = create_account(
            person('teacher.karim', Role.TEACHER, gender=Gender.MALE, contract=contract('six_months')),
            self.manager,
        )
        self.student = create_account(person('student.ali', Role.STUDENT, gender=Gender.MALE), self.manager)
        self.student_two = create_account(person('student.maryam', Role.STUDENT, gender=Gender.FEMALE), self.manager)
        self.other_student = create_account(person('student.herat', Role.STUDENT, gender=Gender.MALE), self.other_manager)
        self.client.force_authenticate(self.manager)
        room = self.client.post('/api/classes/classrooms/', {'name': 'Room 1', 'capacity': 30}, format='json')
        self.assertEqual(room.status_code, 201, room.data)
        self.room_id = room.data['id']
        self.course = self._course('Mathematics', 'MATH', self.teacher.id, '1000.00', 10, 0, '08:00', '09:30')
        self.course_two = self._course('English', 'ENG', self.teacher_two.id, '800.00', 1, 1, '10:00', '11:30')

    def _course(self, name, code, teacher_id, fee, capacity, day, start, end):
        response = self.client.post('/api/courses/', {
            'name': name,
            'code': code,
            'description': f'{name} for the current term.',
            'teacher': teacher_id,
            'duration_hours': 40,
            'start_date': '2026-09-01',
            'end_date': '2026-12-31',
            'fee': fee,
            'capacity': capacity,
            'section_name': 'Section A',
            'schedules': [{
                'day_of_week': day,
                'start_time': start,
                'end_time': end,
                'classroom': self.room_id,
            }],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def _class_id(self, course):
        return course['classes'][0]['id']

    def _enroll(self, student_id, course):
        return self.client.post('/api/enrollments/manual/', {
            'student_id': student_id,
            'course_id': course['id'],
            'class_id': self._class_id(course),
        }, format='json')

    def test_login_returns_role_and_tokens(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/auth/login/', {'username': 'student.ali', 'password': 'Staff@12345'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['role'], Role.STUDENT)

    def test_super_admin_cannot_create_a_course(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/courses/', {
            'name': 'Blocked',
            'description': 'Super admin must not create this.',
            'teacher': self.teacher.id,
            'duration_hours': 10,
            'start_date': '2026-09-01',
            'end_date': '2026-12-31',
            'fee': '100.00',
            'capacity': 5,
            'schedules': [{
                'day_of_week': 2, 'start_time': '08:00', 'end_time': '09:00', 'classroom': self.room_id,
            }],
        }, format='json')
        self.assertEqual(response.status_code, 403, response.data)

    def test_available_managers_exclude_active_ones(self):
        self.client.force_authenticate(self.admin)
        idle = create_account(person('manager.idle', Role.CENTER_MANAGER), self.admin)
        response = self.client.get('/api/users/available-managers/')
        self.assertEqual(response.status_code, 200, response.data)
        ids = [row['id'] for row in response.data]
        self.assertIn(idle.id, ids)
        self.assertNotIn(self.manager.id, ids)
        self.assertNotIn(self.other_manager.id, ids)

    def test_center_cannot_have_two_active_managers(self):
        self.client.force_authenticate(self.admin)
        spare = create_account(person('manager.spare', Role.CENTER_MANAGER), self.admin)
        response = self.client.post(f'/api/centers/{self.center.id}/assign-manager/', {
            'manager_id': spare.id,
            'replace': False,
            'contract': contract(),
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)

    def test_teacher_cannot_hold_two_active_contracts(self):
        self.client.force_authenticate(self.other_manager)
        response = self.client.post('/api/contracts/', {
            'user': self.teacher.id,
            **contract(),
        }, format='json')
        self.assertIn(response.status_code, (400, 403, 409), response.data)

    def test_gender_payment_and_contract_values_are_closed(self):
        self.client.force_authenticate(self.manager)
        gender = self.client.post('/api/users/', person('student.bad', Role.STUDENT, gender='other'), format='json')
        self.assertEqual(gender.status_code, 400, gender.data)
        enrollment = self._enroll(self.student.id, self.course)
        self.assertEqual(enrollment.status_code, 201, enrollment.data)
        invoice_id = self.client.get('/api/finance/invoices/').data['results'][0]['id']
        self.client.force_authenticate(self.finance)
        payment = self.client.post('/api/finance/payments/', {
            'invoice': invoice_id, 'amount': '100.00', 'method': 'card',
        }, format='json')
        self.assertEqual(payment.status_code, 400, payment.data)
        bank = self.client.post('/api/finance/payments/', {
            'invoice': invoice_id, 'amount': '100.00', 'method': 'bank', 'reference': '1',
        }, format='json')
        self.assertEqual(bank.status_code, 400, bank.data)

    def test_student_can_join_two_courses_but_not_two_centers(self):
        first = self._enroll(self.student.id, self.course)
        self.assertEqual(first.status_code, 201, first.data)
        self.client.force_authenticate(self.student)
        own = self.client.post('/api/enrollments/self-enroll/', {
            'course_id': self.course_two['id'],
            'class_id': self._class_id(self.course_two),
        }, format='json')
        self.assertEqual(own.status_code, 201, own.data)
        self.client.force_authenticate(self.other_manager)
        room = self.client.post('/api/classes/classrooms/', {'name': 'Room H', 'capacity': 20}, format='json')
        other_course = self.client.post('/api/courses/', {
            'name': 'History',
            'description': 'Herat history course.',
            'teacher': create_account(person('teacher.herat', Role.TEACHER, gender=Gender.FEMALE, contract=contract()), self.other_manager).id,
            'duration_hours': 20,
            'start_date': '2026-09-01',
            'end_date': '2026-12-31',
            'fee': '500.00',
            'capacity': 10,
            'schedules': [{
                'day_of_week': 3, 'start_time': '12:00', 'end_time': '13:00', 'classroom': room.data['id'],
            }],
        }, format='json')
        self.assertEqual(other_course.status_code, 201, other_course.data)
        blocked = self.client.post('/api/enrollments/manual/', {
            'student_id': self.student.id,
            'course_id': other_course.data['id'],
            'class_id': other_course.data['classes'][0]['id'],
        }, format='json')
        self.assertEqual(blocked.status_code, 403, blocked.data)

    def test_duplicate_and_full_course_are_rejected(self):
        self.assertEqual(self._enroll(self.student.id, self.course_two).status_code, 201)
        duplicate = self._enroll(self.student.id, self.course_two)
        self.assertEqual(duplicate.status_code, 409, duplicate.data)
        full = self._enroll(self.student_two.id, self.course_two)
        self.assertEqual(full.status_code, 409, full.data)

    def test_manual_enrollment_when_self_enrollment_is_off(self):
        self.client.patch(f'/api/centers/{self.center.id}/settings/', {'allow_self_enrollment': False}, format='json')
        self.client.force_authenticate(self.student)
        denied = self.client.post('/api/enrollments/self-enroll/', {
            'course_id': self.course['id'],
            'class_id': self._class_id(self.course),
        }, format='json')
        self.assertEqual(denied.status_code, 400, denied.data)
        self.client.force_authenticate(self.manager)
        allowed = self._enroll(self.student.id, self.course)
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_schedule_conflict_for_teacher(self):
        response = self.client.post('/api/classes/', {
            'course': self.course['id'],
            'name': 'Clash',
            'teacher': self.teacher.id,
            'schedules': [{
                'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00', 'classroom': self.room_id,
            }],
        }, format='json')
        self.assertEqual(response.status_code, 409, response.data)

    def test_attendance_is_present_or_absent_and_manager_corrects_it(self):
        enrollment = self._enroll(self.student.id, self.course)
        self.assertEqual(enrollment.status_code, 201, enrollment.data)
        day = timezone.localdate()
        while day.weekday() != 0:
            day -= timedelta(days=1)
        if day < date(2026, 9, 1):
            day = date(2026, 11, 9)
        self.client.force_authenticate(self.teacher)
        bad = self.client.post('/api/attendance/mark/', {
            'class_id': self._class_id(self.course),
            'date': day.isoformat(),
            'records': [{'student_id': self.student.id, 'status': 'late'}],
        }, format='json')
        self.assertEqual(bad.status_code, 400, bad.data)
        marked = self.client.post('/api/attendance/mark/', {
            'class_id': self._class_id(self.course),
            'date': day.isoformat(),
            'records': [{'student_id': self.student.id, 'status': 'present'}],
        }, format='json')
        self.assertEqual(marked.status_code, 201, marked.data)
        record_id = marked.data['records'][0]['id']
        again = self.client.post('/api/attendance/mark/', {
            'class_id': self._class_id(self.course),
            'date': day.isoformat(),
            'records': [{'student_id': self.student.id, 'status': 'absent'}],
        }, format='json')
        self.assertEqual(again.status_code, 409, again.data)
        teacher_edit = self.client.patch(f'/api/attendance/records/{record_id}/', {'status': 'absent'}, format='json')
        self.assertEqual(teacher_edit.status_code, 403, teacher_edit.data)
        self.client.force_authenticate(self.manager)
        manager_edit = self.client.patch(f'/api/attendance/records/{record_id}/', {'status': 'absent'}, format='json')
        self.assertEqual(manager_edit.status_code, 200, manager_edit.data)
        self.assertEqual(manager_edit.data['status'], 'absent')

    def test_scholarship_installments_and_refund_approval(self):
        enrollment = self._enroll(self.student.id, self.course)
        self.assertEqual(enrollment.status_code, 201, enrollment.data)
        self.client.force_authenticate(self.finance)
        scholarship = self.client.post('/api/finance/scholarships/', {
            'name': 'Merit 10', 'scholarship_type': 'percentage', 'value': '10.00',
        }, format='json')
        self.assertEqual(scholarship.status_code, 201, scholarship.data)
        applied = self.client.post('/api/finance/scholarships/apply/', {
            'scholarship': scholarship.data['id'],
            'enrollment': enrollment.data['id'],
        }, format='json')
        self.assertEqual(applied.status_code, 200, applied.data)
        self.assertEqual(Decimal(applied.data['net_amount']), Decimal('900.00'))
        self.assertEqual(Decimal(applied.data['scholarship_amount']), Decimal('100.00'))
        invoice_id = applied.data['id']
        plan = self.client.post('/api/finance/installments/plan/', {
            'invoice': invoice_id,
            'installments': [
                {'due_date': '2026-10-01', 'amount': '300.00'},
                {'due_date': '2026-11-01', 'amount': '300.00'},
                {'due_date': '2026-12-01', 'amount': '300.00'},
            ],
        }, format='json')
        self.assertEqual(plan.status_code, 201, plan.data)
        self.assertEqual(len(plan.data), 3)
        too_many = self.client.post('/api/finance/installments/plan/', {
            'invoice': invoice_id,
            'installments': [
                {'due_date': '2026-10-01', 'amount': '100.00'},
                {'due_date': '2026-10-15', 'amount': '100.00'},
                {'due_date': '2026-11-01', 'amount': '100.00'},
                {'due_date': '2026-12-01', 'amount': '600.00'},
            ],
        }, format='json')
        self.assertEqual(too_many.status_code, 400, too_many.data)
        paid = self.client.post('/api/finance/payments/', {
            'invoice': invoice_id, 'amount': '300.00', 'method': 'cash',
        }, format='json')
        self.assertEqual(paid.status_code, 201, paid.data)
        refund = self.client.post('/api/finance/refunds/', {
            'invoice': invoice_id, 'amount': '50.00', 'reason': 'Family requested a partial return.',
        }, format='json')
        self.assertEqual(refund.status_code, 201, refund.data)
        finance_approve = self.client.post(f"/api/finance/refunds/{refund.data['id']}/approve/", {}, format='json')
        self.assertEqual(finance_approve.status_code, 403, finance_approve.data)
        self.client.force_authenticate(self.manager)
        approved = self.client.post(f"/api/finance/refunds/{refund.data['id']}/approve/", {
            'decision_note': 'Approved.',
        }, format='json')
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data['status'], 'approved')

    def test_installment_service_rejects_a_fourth_slice(self):
        enrollment = self._enroll(self.student_two.id, self.course)
        self.assertEqual(enrollment.status_code, 201, enrollment.data)
        from apps.finance.models import Invoice
        invoice = Invoice.objects.get(enrollment_id=enrollment.data['id'])
        with self.assertRaises(BusinessRuleError):
            create_installment_plan(
                invoice=invoice,
                installments=[
                    {'due_date': date(2026, 10, 1), 'amount': '250.00'},
                    {'due_date': date(2026, 10, 15), 'amount': '250.00'},
                    {'due_date': date(2026, 11, 1), 'amount': '250.00'},
                    {'due_date': date(2026, 12, 1), 'amount': '250.00'},
                ],
                actor=self.finance,
            )

    def test_finance_manager_cannot_read_another_center(self):
        self.client.force_authenticate(self.other_manager)
        room = self.client.post('/api/classes/classrooms/', {'name': 'Herat Room', 'capacity': 15}, format='json')
        teacher = create_account(person('teacher.h2', Role.TEACHER, contract=contract(), gender=Gender.MALE), self.other_manager)
        created = self.client.post('/api/courses/', {
            'name': 'Physics',
            'description': 'Herat physics course.',
            'teacher': teacher.id,
            'duration_hours': 30,
            'start_date': '2026-09-01',
            'end_date': '2026-12-31',
            'fee': '700.00',
            'capacity': 8,
            'schedules': [{
                'day_of_week': 4, 'start_time': '08:00', 'end_time': '09:00', 'classroom': room.data['id'],
            }],
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.client.force_authenticate(self.finance)
        hidden = self.client.get(f"/api/courses/{created.data['id']}/")
        self.assertEqual(hidden.status_code, 404, hidden.data)

    def test_cross_center_attempt_is_audited(self):
        from apps.common.models import AuditLog
        self.client.force_authenticate(self.student)
        response = self.client.post('/api/enrollments/self-enroll/', {
            'course_id': self.course['id'],
            'class_id': self._class_id(self.course),
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        before = AuditLog.objects.filter(action='security.cross_center').count()
        self.client.force_authenticate(self.other_student)
        denied = self.client.post('/api/enrollments/self-enroll/', {
            'course_id': self.course['id'],
            'class_id': self._class_id(self.course),
        }, format='json')
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertGreater(AuditLog.objects.filter(action='security.cross_center').count(), before)

    def test_fixed_scholarship_cannot_exceed_the_fee(self):
        enrollment = self._enroll(self.student.id, self.course)
        self.client.force_authenticate(self.finance)
        scholarship = self.client.post('/api/finance/scholarships/', {
            'name': 'Too big', 'scholarship_type': 'fixed', 'value': '5000.00',
        }, format='json')
        response = self.client.post('/api/finance/scholarships/apply/', {
            'scholarship': scholarship.data['id'],
            'enrollment': enrollment.data['id'],
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
