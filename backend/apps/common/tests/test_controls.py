"""Authorization, policy resolution, privacy, and lifecycle gaps.

These tests call the API. Permission checks read the database, so a change is
visible on the next request even when the access token is unchanged.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, connection
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Contract, User
from apps.accounts.services import create_account
from apps.centers.models import GlobalSettings
from apps.centers.services import assign_manager, create_center, set_center_active
from apps.common.choices import Gender, Role
from apps.common.money import split_amount
from apps.common.notifications import notify
from apps.common.tests.test_business_rules import contract, person
from apps.courses.models import Course
from apps.enrollments.models import Enrollment
from apps.finance.models import Invoice
from apps.reports.services import integrity_report


class ControlTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'superadmin', 'superadmin@tuition.local', 'Admin@12345',
            first_name='System', last_name='Admin', phone='+93700000000', gender=Gender.MALE,
        )
        self.center = create_center({'name': 'Kabul Star', 'code': 'KBL', 'city': 'Kabul'}, self.admin)
        self.other = create_center({'name': 'Herat Academy', 'code': 'HRT', 'city': 'Herat'}, self.admin)
        self.manager = create_account(person('manager.kabul', Role.CENTER_MANAGER), self.admin)
        assign_manager(center=self.center, manager=self.manager, contract_data=contract(), actor=self.admin)
        set_center_active(self.center, True, self.admin)
        self.manager = User.objects.get(pk=self.manager.pk)
        self.other_manager = create_account(person('manager.herat', Role.CENTER_MANAGER), self.admin)
        assign_manager(center=self.other, manager=self.other_manager, contract_data=contract(), actor=self.admin)
        set_center_active(self.other, True, self.admin)
        self.finance = create_account(person('finance.kabul', Role.FINANCE_MANAGER, contract=contract()), self.manager)
        self.teacher = create_account(person('teacher.zahra', Role.TEACHER, contract=contract()), self.manager)
        self.student = create_account(person('student.ali', Role.STUDENT), self.manager)
        self.student_two = create_account(person('student.maryam', Role.STUDENT), self.manager)
        self.client.force_authenticate(self.manager)
        room = self.client.post('/api/classes/classrooms/', {'name': 'Room 1', 'capacity': 30}, format='json')
        self.room_id = room.data['id']
        course = self.client.post('/api/courses/', {
            'name': 'Mathematics', 'code': 'MATH', 'description': 'Term course.',
            'teacher': self.teacher.id, 'duration_hours': 40,
            'start_date': '2026-09-01', 'end_date': '2026-12-31', 'fee': '1000.00', 'capacity': 2,
            'section_name': 'Section A',
            'schedules': [{'day_of_week': 0, 'start_time': '08:00', 'end_time': '09:30', 'classroom': self.room_id}],
        }, format='json')
        self.assertEqual(course.status_code, 201, course.data)
        self.course = course.data
        self.class_id = course.data['classes'][0]['id']

    def _enroll(self, student):
        self.client.force_authenticate(self.manager)
        response = self.client.post('/api/enrollments/manual/', {
            'student_id': student.id, 'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_report_preparation_denial_blocks_every_prepare_route(self):
        token = str(RefreshToken.for_user(self.finance).access_token)
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        created = self.client.post('/api/reports/financial/', {
            'title': 'October', 'period_start': '2026-10-01', 'period_end': '2026-10-31',
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.client.force_authenticate(self.admin)
        changed = self.client.post('/api/permissions/overrides/', {
            'role': 'finance_manager', 'code': 'reports.prepare', 'allowed': False,
            'reason': 'Pause official drafts until the review.',
        }, format='json')
        self.assertEqual(changed.status_code, 200, changed.data)
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        again = self.client.post('/api/reports/financial/', {
            'title': 'November', 'period_start': '2026-11-01', 'period_end': '2026-11-30',
        }, format='json')
        submitted = self.client.post(f"/api/reports/financial/{created.data['id']}/submit/", {}, format='json')
        revised = self.client.post(f"/api/reports/financial/{created.data['id']}/revise/", {}, format='json')
        bulk = self.client.post('/api/reports/financial/bulk/', {}, format='json')
        self.assertEqual(again.status_code, 403, again.data)
        self.assertEqual(submitted.status_code, 403, submitted.data)
        self.assertEqual(revised.status_code, 403, revised.data)
        self.assertIn(bulk.status_code, (404, 405))

    def test_permission_preview_history_and_restore(self):
        self.client.force_authenticate(self.admin)
        preview = self.client.post('/api/permissions/preview/', {
            'role': 'finance_manager', 'code': 'exports.invoices', 'allowed': False,
            'reason': 'Exports are paused for this review.',
        }, format='json')
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertIn('GET /api/reports/export/invoices/', preview.data['closes'])
        self.assertFalse(preview.data['lockout'])
        self.assertIn('cannot remove', preview.data['lockout_note'])
        applied = self.client.post('/api/permissions/overrides/', {
            'role': 'finance_manager', 'code': 'exports.invoices', 'allowed': False,
            'reason': 'Exports are paused for this review.',
        }, format='json')
        self.assertEqual(applied.status_code, 200, applied.data)
        self.client.force_authenticate(self.finance)
        self.assertEqual(self.client.get('/api/reports/export/invoices/').status_code, 403)
        self.client.force_authenticate(self.admin)
        history = self.client.get('/api/permissions/history/')
        self.assertEqual(history.data[0]['version'], applied.data['version'])
        self.assertEqual(history.data[0]['actor'], 'superadmin')
        restored = self.client.post('/api/permissions/restore/', {
            'version': applied.data['version'],
            'reason': 'The review is finished.',
        }, format='json')
        self.assertEqual(restored.status_code, 200, restored.data)
        self.assertTrue(restored.data['allowed'])
        self.client.force_authenticate(self.finance)
        self.assertEqual(self.client.get('/api/reports/export/invoices/').status_code, 200)
        matrix = self.client.get('/api/permissions/matrix/')
        self.client.force_authenticate(self.admin)
        matrix = self.client.get('/api/permissions/matrix/')
        self.assertEqual(matrix.status_code, 200, matrix.data)
        self.assertEqual(len(matrix.data['roles']), 5)
        protected = next(row for row in matrix.data['rows'] if row['code'] == 'finance.collect')
        self.assertTrue(protected['protected'])
        self.assertFalse(protected['cells']['teacher']['configurable'])

    def test_policy_resolution_and_afn_label(self):
        self.client.force_authenticate(self.admin)
        global_change = self.client.patch('/api/settings/global/', {
            'allow_self_enrollment': False,
            'require_enrollment_approval': True,
            'max_installments': 2,
            'allow_waitlist': False,
            'allow_student_refund_requests': False,
            'currency_label': 'USD',
            'note': 'Tighten the ceiling for the new term.',
        }, format='json')
        self.assertEqual(global_change.status_code, 400, global_change.data)
        global_change = self.client.patch('/api/settings/global/', {
            'allow_self_enrollment': False,
            'require_enrollment_approval': True,
            'max_installments': 2,
            'allow_waitlist': False,
            'allow_student_refund_requests': False,
            'note': 'Tighten the ceiling for the new term.',
        }, format='json')
        self.assertEqual(global_change.status_code, 200, global_change.data)
        self.assertEqual(global_change.data['currency_label'], 'AFN')
        self.client.force_authenticate(self.manager)
        effective = self.client.get('/api/settings/effective/')
        rules = effective.data['rules']
        self.assertFalse(rules['self_enrollment']['effective'])
        self.assertEqual(rules['self_enrollment']['source'], 'global_allows AND center_enables')
        self.assertTrue(rules['approval_required']['effective'])
        self.assertEqual(rules['installment_limit']['effective'], 2)
        self.assertFalse(rules['waitlist']['effective'])
        self.assertFalse(rules['student_refund_requests']['effective'])
        self.assertEqual(rules['currency']['effective'], 'AFN')
        self._enroll(self.student)
        invoice = Invoice.objects.get(student=self.student)
        self.client.force_authenticate(self.student)
        closed = self.client.post('/api/enrollments/waitlist/', {
            'course_id': self.course['id'], 'class_id': self.class_id,
        }, format='json')
        self.assertEqual(closed.status_code, 400, closed.data)
        self.client.force_authenticate(self.finance)
        paid = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '20.00', 'method': 'cash', 'idempotency_key': 'afn-20',
        }, format='json')
        self.assertEqual(paid.status_code, 201, paid.data)
        self.client.force_authenticate(self.student)
        refund = self.client.post('/api/finance/refunds/', {
            'invoice': invoice.id, 'amount': '10.00', 'reason': 'Please return part of the fee.',
        }, format='json')
        self.assertEqual(refund.status_code, 400, refund.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.net_amount, Decimal('1000.00'))
        self.assertEqual(GlobalSettings.load().currency_label, 'AFN')

    def test_payment_key_is_required(self):
        self._enroll(self.student)
        invoice = Invoice.objects.get(student=self.student)
        self.client.force_authenticate(self.finance)
        missing = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '10.00', 'method': 'cash',
        }, format='json')
        self.assertEqual(missing.status_code, 400, missing.data)
        self.assertEqual(invoice.payments.count(), 0)

    def test_teacher_correction_request_does_not_change_the_mark_until_approval(self):
        enrolled = self._enroll(self.student)
        from datetime import datetime
        Enrollment.objects.filter(pk=enrolled['id']).update(created_at=timezone.make_aware(datetime(2026, 9, 1, 8, 0)))
        day = timezone.localdate()
        while day.weekday() != 0:
            day -= timedelta(days=1)
        self.client.force_authenticate(self.teacher)
        marked = self.client.post('/api/attendance/mark/', {
            'class_id': self.class_id, 'date': day.isoformat(),
            'records': [{'student_id': self.student.id, 'status': 'present'}],
        }, format='json')
        record_id = marked.data['records'][0]['id']
        requested = self.client.post('/api/attendance/correction-requests/', {
            'record_id': record_id, 'status': 'absent', 'reason': 'The student arrived after the register closed.',
        }, format='json')
        self.assertEqual(requested.status_code, 201, requested.data)
        self.assertEqual(marked.data['records'][0]['status'], 'present')
        direct = self.client.patch(f'/api/attendance/records/{record_id}/', {
            'status': 'absent', 'reason': 'Teachers cannot apply this themselves.',
        }, format='json')
        self.assertEqual(direct.status_code, 403, direct.data)
        self.client.force_authenticate(self.manager)
        decided = self.client.post('/api/attendance/decide-correction/', {
            'id': requested.data['id'], 'approve': True, 'note': 'Confirmed with the gate log.',
        }, format='json')
        self.assertEqual(decided.status_code, 200, decided.data)
        from apps.attendance.models import AttendanceRecord
        self.assertEqual(AttendanceRecord.objects.get(pk=record_id).status, 'absent')

    def test_expired_contract_stops_writes_and_can_be_renewed(self):
        staff = Contract.objects.get(user=self.teacher, status='active')
        Contract.objects.filter(pk=staff.pk).update(end_date=timezone.localdate() - timedelta(days=1))
        self.client.force_authenticate(self.teacher)
        blocked = self.client.post('/api/attendance/mark/', {
            'class_id': self.class_id, 'date': '2026-11-09',
            'records': [{'student_id': self.student.id, 'status': 'present'}],
        }, format='json')
        self.assertEqual(blocked.status_code, 400, blocked.data)
        self.assertFalse(Contract.objects.filter(user=self.teacher, status='active').exists())
        self.client.force_authenticate(self.manager)
        renewed = self.client.post('/api/contracts/', {'user': self.teacher.id, **contract()}, format='json')
        self.assertEqual(renewed.status_code, 201, renewed.data)

    def test_future_contract_does_not_authorize_today(self):
        staff = Contract.objects.get(user=self.teacher, status='active')
        Contract.objects.filter(pk=staff.pk).update(start_date=timezone.localdate() + timedelta(days=10))
        self.client.force_authenticate(self.teacher)
        blocked = self.client.post('/api/attendance/mark/', {
            'class_id': self.class_id, 'date': '2026-11-09',
            'records': [{'student_id': self.student.id, 'status': 'present'}],
        }, format='json')
        self.assertEqual(blocked.status_code, 400, blocked.data)

    def test_failed_replacement_keeps_the_current_manager(self):
        newbie = create_account(person('manager.new', Role.CENTER_MANAGER), self.admin)
        bad = contract()
        bad['end_date'] = bad['start_date'] - timedelta(days=3)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/centers/{self.center.id}/assign-manager/', {
            'manager_id': newbie.id, 'replace': True, 'contract': bad,
        }, format='json')
        self.assertGreaterEqual(response.status_code, 400, response.data)
        self.center.refresh_from_db()
        self.assertEqual(self.center.get_active_manager().id, self.manager.id)

    def test_deactivated_manager_blocks_operations_until_replacement(self):
        self._enroll(self.student)
        invoice = Invoice.objects.get(student=self.student)
        self.manager.is_active = False
        self.manager.save(update_fields=['is_active'])
        self.client.force_authenticate(self.finance)
        blocked = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '10.00', 'method': 'cash', 'idempotency_key': 'while-inactive',
        }, format='json')
        self.assertEqual(blocked.status_code, 400, blocked.data)
        self.assertIn('eligible manager', str(blocked.data))
        replacement = create_account(person('manager.next', Role.CENTER_MANAGER), self.admin)
        self.client.force_authenticate(self.admin)
        assigned = self.client.post(f'/api/centers/{self.center.id}/assign-manager/', {
            'manager_id': replacement.id, 'replace': True, 'contract': contract(),
        }, format='json')
        self.assertEqual(assigned.status_code, 200, assigned.data)
        self.client.force_authenticate(self.finance)
        paid = self.client.post('/api/finance/payments/', {
            'invoice': invoice.id, 'amount': '10.00', 'method': 'cash', 'idempotency_key': 'after-replacement',
        }, format='json')
        self.assertEqual(paid.status_code, 201, paid.data)

    def test_integrity_checker_reports_controlled_inconsistencies_without_writing(self):
        self._enroll(self.student)
        self._enroll(self.student_two)
        invoice = Invoice.objects.get(student=self.student)
        before = invoice.updated_at
        Invoice.objects.filter(pk=invoice.pk).update(paid_amount=Decimal('5000.00'), refunded_amount=Decimal('9000.00'))
        Course.objects.filter(pk=self.course['id']).update(capacity=1)
        Enrollment.objects.filter(student=self.student_two).update(center_id=self.other.id)
        self.manager.is_active = False
        self.manager.save(update_fields=['is_active'])
        issues = {row['code'] for row in integrity_report()}
        self.assertIn('paid_above_net', issues)
        self.assertIn('refunded_above_paid', issues)
        self.assertIn('capacity_exceeded', issues)
        self.assertIn('enrollment_center_mismatch', issues)
        self.assertIn('inactive_manager_lock', issues)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('5000.00'))
        self.assertEqual(invoice.updated_at, before)
        from django.db import transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Enrollment.objects.create(
                    student=self.student, course_id=self.course['id'], course_class_id=self.class_id,
                    center=self.center, status='active', source='manual',
                )

    def test_privacy_and_scope(self):
        self._enroll(self.student)
        self._enroll(self.student_two)
        self.client.force_authenticate(self.student)
        roster = self.client.get(f'/api/classes/{self.class_id}/students/')
        self.assertEqual(roster.status_code, 403, roster.data)
        invoices = self.client.get('/api/finance/invoices/')
        self.assertTrue(all(row['student']['id'] == self.student.id for row in invoices.data['results']))
        photo = self.client.get(f'/api/profile/photo/{self.student_two.id}/')
        self.assertEqual(photo.status_code, 403, photo.status_code)
        self.client.force_authenticate(self.teacher)
        visible = self.client.get(f'/api/classes/{self.class_id}/students/')
        self.assertEqual(visible.status_code, 200, visible.data)
        classmate = next(row for row in visible.data if row['id'] == self.student.id)
        self.assertEqual(classmate['email'], '')
        self.assertIsNone(classmate['photo_url'])
        self.client.force_authenticate(self.finance)
        self.assertEqual(self.client.get(f'/api/classes/{self.class_id}/students/').status_code, 403)
        self.client.force_authenticate(self.manager)
        other_room = self.client.post('/api/classes/classrooms/', {'name': 'Nope', 'capacity': 5}, format='json')
        self.client.force_authenticate(self.other_manager)
        hidden = self.client.get(f"/api/classes/classrooms/{other_room.data['id']}/")
        self.assertEqual(hidden.status_code, 404, hidden.data)
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get('/api/reports/integrity/').status_code, 403)
        self.assertEqual(self.client.get('/api/permissions/matrix/').status_code, 403)
        self.client.force_authenticate(self.finance)
        self.assertEqual(self.client.patch('/api/settings/global/', {'max_installments': 1}, format='json').status_code, 403)

    def test_classroom_capacity_has_no_update_route(self):
        self.client.force_authenticate(self.manager)
        response = self.client.patch(f'/api/classes/classrooms/{self.room_id}/', {'capacity': 1}, format='json')
        self.assertEqual(response.status_code, 405, response.status_code)

    def test_completion_waits_for_the_course_end_and_leaves_history(self):
        enrolled = self._enroll(self.student)
        self.client.force_authenticate(self.manager)
        early = self.client.post(f"/api/enrollments/{enrolled['id']}/complete/", {}, format='json')
        self.assertEqual(early.status_code, 400, early.data)
        Course.objects.filter(pk=self.course['id']).update(end_date=timezone.localdate() - timedelta(days=1))
        done = self.client.post(f"/api/enrollments/{enrolled['id']}/complete/", {}, format='json')
        self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(done.data['status'], 'completed')
        self.client.force_authenticate(self.student)
        history = self.client.get('/api/enrollments/')
        self.assertTrue(any(row['id'] == enrolled['id'] and row['status'] == 'completed' for row in history.data['results']))

    def test_super_admin_does_not_see_draft_reports_by_default(self):
        self.client.force_authenticate(self.finance)
        created = self.client.post('/api/reports/financial/', {
            'title': 'October', 'period_start': '2026-10-01', 'period_end': '2026-10-31',
        }, format='json')
        self.client.force_authenticate(self.admin)
        hidden = self.client.get('/api/reports/financial/')
        self.assertFalse(any(row['id'] == created.data['id'] for row in hidden.data['results']))
        visible = self.client.get('/api/reports/financial/?status=draft')
        self.assertTrue(any(row['id'] == created.data['id'] for row in visible.data['results']))

    def test_notifications_are_deduplicated_and_private(self):
        first = notify(self.student, 'test', 'Hello', 'Body', dedupe_key='same-notice')
        second = notify(self.student, 'test', 'Hello again', 'Other', dedupe_key='same-notice')
        self.assertEqual(first.id, second.id)
        self.client.force_authenticate(self.teacher)
        foreign = self.client.get('/api/notifications/')
        self.assertFalse(any(row['id'] == first.id for row in foreign.data))
        denied = self.client.post(f'/api/notifications/{first.id}/read/', {}, format='json')
        self.assertEqual(denied.status_code, 400, denied.data)

    def test_installment_rounding_lands_on_the_last_share(self):
        shares = split_amount(Decimal('100.00'), 3)
        self.assertEqual(shares, [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')])
        self.assertEqual(sum(shares), Decimal('100.00'))

    def test_added_migrations_do_not_delete_tables(self):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        destructive = {'DeleteModel', 'RemoveField', 'DeleteModel'}
        for (app, name), migration in loader.disk_migrations.items():
            if app not in {'attendance', 'centers', 'common', 'enrollments', 'finance', 'reports'}:
                continue
            if name == '0001_initial':
                continue
            for operation in migration.operations:
                self.assertNotIn(operation.__class__.__name__, {'DeleteModel', 'RemoveField'})

