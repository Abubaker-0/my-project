# Rule traceability

| Rule | Where it is enforced | Test |
| --- | --- | --- |
| Centers are created inactive and need a manager before activation | `centers.services.create_center`, `set_center_active` | existing center tests |
| One active manager and one active staff contract | unique `active_manager_lock`, `active_contract_lock` | existing contract tests |
| Contract date window in Asia/Kabul | `accounts.services.active_contract_for` | operational checks used by workflow tests |
| No cross-center reads or writes | `assert_same_center` and queryset filters | `test_student_cannot_enroll_in_another_center`, `test_manager_cannot_enroll_into_another_center` |
| One open enrollment per student and course | `Enrollment.active_key` | existing duplicate enrollment test |
| Pending and active consume seats; waitlist does not | `enroll`, `join_waitlist` | `test_waitlist_does_not_invoice_and_promotion_rechecks_capacity` |
| Class belongs to the course and center | `enroll` | existing enrollment tests |
| Classroom capacity rechecked in the enrollment transaction | `enroll` room check | capacity test uses a room of 30 so the course limit binds first |
| Attendance is class plus date; roster is historical | `eligible_roster`, `mark_attendance` | attendance test with enrollment backdated to 2026-09-01 |
| Manager correction needs a reason and keeps the original mark | `correct_attendance`, `AttendanceCorrection` | `test_correction_keeps_the_original_mark` |
| Teacher cannot edit a submitted register | `correct_attendance` role check | attendance test expects 403 |
| Payment amount is positive and not above outstanding | `record_payment` | existing payment tests |
| Idempotent payment retry | `Payment.idempotency_key` unique with `received_by` | `test_identical_payment_retry_returns_the_same_receipt` |
| At most one scholarship grant | `apply_scholarship` | existing scholarship test; second grant is `ConflictError` |
| Installments sum to the net fee; unpaid plan replacement is archived | `create_installment_plan`, `split_amount` | existing installment test |
| Refund ceiling is received minus approved minus pending | `request_refund`, `decide_refund` | existing refund tests |
| Refund approval is not a bank transfer | receipt and refund copy | receipt test asserts the statement |
| Withdrawal does not void the invoice | `decide_withdrawal` | `test_withdrawal_keeps_the_invoice` |
| Completion is not an open enrollment and waits for the course end | `complete_enrollment` | service rule; UI posts to `/enrollments/{id}/complete/` |
| Report snapshot frozen; return needs a new revision | `return_report`, `revise_report` | `test_returned_report_needs_a_new_revision` |
| Super admin official list defaults to sent reports | `FinancialReportViewSet.get_queryset` | `test_super_admin_does_not_see_draft_reports_by_default` |
| Protected separation of duties cannot be disabled | `set_permission_override` | `test_protected_permission_cannot_be_denied` |
| Export and report preparation can be narrowed | `has_permission` | `test_export_honors_a_global_restriction` |
| Policy save keeps a version and does not rewrite invoices | `record_policy` | `test_policy_save_keeps_a_version` |
| Integrity dashboard is read-only and super admin only | `integrity_report`, `IntegrityView` | `test_integrity_is_read_only_for_super_admin` |
| Contract alerts are in-app and idempotent | `notify_contract_expirations` | unique `dedupe_key`; command not run on MySQL |
| Students do not receive another student's email, phone, or photo | `UserBriefSerializer.to_representation`, `ProfilePhotoView` | `test_privacy_and_scope` |
| Report preparation denial covers create, submit, and revise | `create_financial_report`, `submit_report`, `revise_report` | `test_report_preparation_denial_blocks_every_prepare_route` |
| Payment key is required and retries reuse it | `record_payment` | `test_payment_key_is_required` and the idempotency races on MariaDB and MySQL 8.0.46 |
| Policy formulas and AFN label | `resolve_policy` | `test_policy_resolution_and_afn_label` |
| Eligible manager and contract renewal | `assert_operational`, `assign_manager` | contract lifecycle tests in `test_controls` |
| Two seats, payments, refunds, and promotions cannot both commit | row locks and unique keys | `test_concurrency` on MariaDB 10.11 and MySQL 8.0.46; skipped on SQLite |
