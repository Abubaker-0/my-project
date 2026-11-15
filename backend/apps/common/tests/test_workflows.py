"""Workflow additions: permissions, waitlist, receipts, reports, and attendance history."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.choices import Gender, Role
from apps.common.models import Notification
from apps.common.tests.test_business_rules import contract, person
from apps.accounts.services import create_account
from apps.centers.services import assign_manager, create_center, set_center_active
from apps.finance.models import Invoice


class WorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'superadmin', 'superadmin@tuition.local', 'Admin@12345',
            first_name='System', last_name='Admin', phone='+93700000000', gender=Gender.MALE,
        )
        self.center = create_center({'name': 'Kabul Star', 'code': 'KBL', 'city': 'Kabul'}, self.admin)
        self.assertFalse(self.center.is_active)
        self.manager = create_account(person('manager.kabul', Role.CENTER_MANAGER), self.admin)
        assign_manager(center=self.center, manager=self.manager, contract_data=contract(), actor=self.admin)
        set_center_active(self.center, True, self.admin)
        self.manager = User.objects.get(pk=self.manager.pk)
        self.finance = create_account(person('finance.kabul', Role.FINANCE_MANAGER, contract=contract()), self.manager)
        self.teacher = create_account(person('teacher.zahra', Role.TEACHER, contract=contract()), self.manager)
        self.student = create_account(person('student.ali', Role.STUDENT), self.manager)
        self.client.force_authenticate(self.manager)
        room = self.client.post('/api/classes/classrooms/', {'name': 'Room 1', 'capacity': 30}, format='json')
        self.room_id = room.data['id']
        course = self.client.post('/api/courses/', {
            'name': 'Mathematics', 'code': 'MATH', 'description': 'Term course.',
            'teacher': self.teacher.id, 'duration_hours': 40,
            'start_date': '2026-09-01', 'end_date': '2026-12-31', 'fee': '1000.00', 'capacity': 1,
            'section_name': 'Section A',
            'schedules': [{'day_of_week': 0, 'start_time': '08:00', 'end_time': '09:30', 'classroom': self.room_id}],
        }, format='json')
        self.assertEqual(course.status_code, 201, course.data)
        self.course = course.data
        self.class_id = course.data['classes'][0]['id']

    def test_protected_permission_cannot_be_disabled(self):
        self.client.force_authenticate(self.admin)
        denied = self.client.post('/api/permissions/overrides/', {
            'role': 'finance_manager', 'code': 'finance.refund_decide', 'allowed': False,
            'reason': 'This duty stays with the center manager.',
        }, format='json')
        self.assertEqual(denied.status_code, 400, denied.data)
        narrowed = self.client.post('/api/permissions/overrides/', {
            'role': 'finance_manager', 'code': 'exports.invoices', 'allowed': False,
            'reason': 'Finance should not export this month.',
        }, format='json')
        self.assertEqual(narrowed.status_code, 200, narrowed.data)
        self.client.force_authenticate(self.finance)
        export = self.client.get('/api/reports/export/invoices/')
        self.assertEqual(export.status_code, 403, export.status_code)
        effective = self.client.get('/api/permissions/effective/')
        self.assertEqual(effective.status_code, 200)
        finance_collect = next(row for row in effective.data['permissions'] if row['code'] == 'finance.collect')
        self.assertTrue(finance_collect['allowed'])
        self.assertEqual(finance_collect['source'], 'protected')

    def test_waitlist_does_not_invoice_and_promotion_rechecks_capacity(self):
        self.client.force_authenticate(self.manager)
        first = self.client.post('/api/enrollments/manual/', {
            'student_id': self.student.id, 'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        other = create_account(person('student.omar', Role.STUDENT), self.manager)
        self.client.force_authenticate(other)
        waiting = self.client.post('/api/enrollments/waitlist/', {
            'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        self.assertEqual(waiting.status_code, 201, waiting.data)
        self.assertEqual(Invoice.objects.filter(student=other).count(), 0)
        self.client.force_authenticate(self.manager)
        promoted = self.client.post('/api/enrollments/promote-waitlist/', {'id': waiting.data['id']}, format='json')
        self.assertEqual(promoted.status_code, 409, promoted.data)

    def test_payment_idempotency_and_receipt(self):
        self.client.force_authenticate(self.manager)
        enrolled = self.client.post('/api/enrollments/manual/', {
            'student_id': self.student.id, 'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        invoice = Invoice.objects.get(enrollment_id=enrolled.data['id'])
        self.client.force_authenticate(self.finance)
        first = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '100.00', 'method': 'cash', 'idempotency_key': 'pay-1',
        }, format='json')
        second = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '100.00', 'method': 'cash', 'idempotency_key': 'pay-1',
        }, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertFalse(first.data['replayed'])
        self.assertEqual(second.status_code, 200, second.data)
        self.assertTrue(second.data['replayed'])
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(invoice.payments.count(), 1)
        clash = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '50.00', 'method': 'cash', 'idempotency_key': 'pay-1',
        }, format='json')
        self.assertEqual(clash.status_code, 409, clash.data)
        receipt = self.client.get(f"/api/finance/payments/{first.data['id']}/receipt/")
        self.assertEqual(receipt.status_code, 200, receipt.data)
        self.assertIn('not a bank transfer', receipt.data['statement'])
        self.client.force_authenticate(self.student)
        own = self.client.get(f"/api/finance/payments/{first.data['id']}/receipt/")
        self.assertEqual(own.status_code, 200)

    def test_withdrawal_keeps_the_invoice(self):
        self.client.force_authenticate(self.manager)
        enrolled = self.client.post('/api/enrollments/manual/', {
            'student_id': self.student.id, 'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        invoice = Invoice.objects.get(enrollment_id=enrolled.data['id'])
        self.client.force_authenticate(self.student)
        request = self.client.post(f"/api/enrollments/{enrolled.data['id']}/withdraw/", {
            'reason': 'I need to leave this course.',
        }, format='json')
        self.assertEqual(request.status_code, 201, request.data)
        self.assertTrue(Notification.objects.filter(kind='withdrawal').exists())
        self.client.force_authenticate(self.manager)
        decided = self.client.post('/api/enrollments/decide-withdrawal/', {
            'id': request.data['id'], 'approve': True, 'note': 'Approved without a refund.',
        }, format='json')
        self.assertEqual(decided.status_code, 200, decided.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.net_amount, Decimal('1000.00'))
        self.assertEqual(invoice.enrollment.status, 'withdrawn')

    def test_returned_report_keeps_its_snapshot_and_links_a_revision(self):
        self.client.force_authenticate(self.finance)
        created = self.client.post('/api/reports/financial/', {
            'title': 'October', 'period_start': '2026-10-01', 'period_end': '2026-10-31',
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        submitted = self.client.post(f"/api/reports/financial/{created.data['id']}/submit/", {}, format='json')
        self.assertEqual(submitted.status_code, 200, submitted.data)
        self.client.force_authenticate(self.manager)
        returned = self.client.post(f"/api/reports/financial/{created.data['id']}/return/", {
            'note': 'Please split the cash and bank totals.',
        }, format='json')
        self.assertEqual(returned.status_code, 200, returned.data)
        frozen = returned.data['snapshot']
        self.client.force_authenticate(self.finance)
        revision = self.client.post(f"/api/reports/financial/{created.data['id']}/revise/", {}, format='json')
        self.assertEqual(revision.status_code, 201, revision.data)
        self.assertEqual(revision.data['previous'], created.data['id'])
        self.assertEqual(revision.data['revision'], 2)
        original = self.client.get(f"/api/reports/financial/{created.data['id']}/")
        self.assertEqual(original.data['snapshot'], frozen)
        self.assertEqual(original.data['status'], 'returned')

    def test_correction_requires_a_reason_and_keeps_history(self):
        self.client.force_authenticate(self.manager)
        enrolled = self.client.post('/api/enrollments/manual/', {
            'student_id': self.student.id, 'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        from datetime import datetime
        from apps.enrollments.models import Enrollment
        Enrollment.objects.filter(pk=enrolled.data['id']).update(
            created_at=timezone.make_aware(datetime(2026, 9, 1, 8, 0)),
        )
        day = timezone.localdate()
        while day.weekday() != 0:
            day -= timedelta(days=1)
        self.client.force_authenticate(self.teacher)
        marked = self.client.post('/api/attendance/mark/', {
            'class_id': self.class_id,
            'date': day.isoformat(),
            'records': [{'student_id': self.student.id, 'status': 'present'}],
        }, format='json')
        self.assertEqual(marked.status_code, 201, marked.data)
        record_id = marked.data['records'][0]['id']
        self.client.force_authenticate(self.manager)
        missing = self.client.patch(f'/api/attendance/records/{record_id}/', {'status': 'absent'}, format='json')
        self.assertEqual(missing.status_code, 400, missing.data)
        corrected = self.client.patch(f'/api/attendance/records/{record_id}/', {
            'status': 'absent', 'reason': 'Register was marked before the student signed in.',
        }, format='json')
        self.assertEqual(corrected.status_code, 200, corrected.data)
        from apps.attendance.models import AttendanceCorrection
        self.assertEqual(AttendanceCorrection.objects.get(record_id=record_id).old_status, 'present')

    def test_policy_change_is_versioned_and_prospective(self):
        self.client.force_authenticate(self.manager)
        changed = self.client.patch(f'/api/centers/{self.center.id}/settings/', {'max_installments': 2}, format='json')
        self.assertEqual(changed.status_code, 200, changed.data)
        history = self.client.get(f'/api/centers/{self.center.id}/settings/history/')
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual(history.data[0]['payload']['max_installments'], 2)
        effective = self.client.get('/api/settings/effective/')
        self.assertEqual(effective.data['rules']['installment_limit']['effective'], 2)
        self.assertIn('existing plan', effective.data['rules']['installment_limit']['effect'])

    def test_integrity_dashboard_is_super_admin_only(self):
        self.client.force_authenticate(self.manager)
        denied = self.client.get('/api/reports/integrity/')
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.admin)
        allowed = self.client.get('/api/reports/integrity/')
        self.assertEqual(allowed.status_code, 200)
        self.assertIn('issues', allowed.data)
