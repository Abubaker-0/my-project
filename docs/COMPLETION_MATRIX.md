# Completion matrix

Labels: verified means an automated test exercised the server rule. A screen or a document is not that evidence.

| Requirement | Where | Server enforcement | Frontend | Evidence | Gap |
| --- | --- | --- | --- | --- | --- |
| Five roles and centre isolation | services and querysets | role and centre checks | existing pages | business-rule tests, `test_privacy_and_scope` | verified |
| Inactive centre and one manager | `centers.services` | unique locks, activation check | centres UI | business-rule tests, replacement tests | verified |
| Eligible manager for writes | `assert_operational`, `get_active_manager` | date window, active user | errors from the API | contract lifecycle tests | verified |
| Future and expired contracts | `active_contract_for`, `Contract.save` | write-time refresh | contract page | `test_future_contract_does_not_authorize_today`, `test_expired_contract_stops_writes_and_can_be_renewed` | verified |
| Failed replacement rolls back | `assign_manager` | one transaction | assign form | `test_failed_replacement_keeps_the_current_manager` | verified |
| Permission catalog for five roles | `permissions_catalog.py` | ceiling in code | governance matrix | `test_permission_preview_history_and_restore` | verified |
| Protected duties cannot be denied | `set_permission_override` | rejected before save | locked cells | `test_protected_permission_cannot_be_disabled` | verified |
| Configurable grants only where a feature exists | reports, exports, waitlist promotion, correction requests | `has_permission` on those routes | matrix buttons | report denial test | verified |
| `reports.prepare` covers create, submit, and revise | report services | 403 on each route | reports page | JWT test, including a missing bulk URL | verified |
| Permission change without a new token | database read on each request | not stored in the JWT | governance page | same access token denied after the change | verified |
| Preview, reason, version, restore | `PermissionChange` | reason required | governance page | preview and restore test | verified |
| No self-lockout of governance | protected `policies.manage` | cannot be stored as a denial | lockout note | preview `lockout` is false and the note is returned | verified |
| Policy resolution | `centers/policy.py` | enroll, waitlist, refunds, installment cap | settings page | `test_policy_resolution_and_afn_label` | verified |
| AFN only | `update_global_settings` | non-AFN rejected | currency field disabled | same test; invoice net unchanged | verified |
| Exports are a permission, not a second policy | catalog | export view | governance | export 403 after denial | verified |
| Payment idempotency required | `record_payment` | key required, unique, row locks | dialog keeps one key | SQLite, MariaDB 10.11, and MySQL 8.0.46 CI | verified |
| Waitlist does not reserve or invoice | `join_waitlist` | no invoice | course page and manager panel | workflow test | verified |
| Withdrawal keeps the invoice | `decide_withdrawal` | invoice untouched | my courses | workflow test | verified |
| Completion after course end | `complete_enrollment` | date check | enrollments page | `test_completion_waits_for_the_course_end_and_leaves_history` | verified |
| Attendance daily, historical roster | `eligible_roster` | one row per class and date | attendance page | attendance tests on SQLite and MariaDB | verified |
| Teacher correction request | `AttendanceCorrectionRequest` | mark unchanged until approval | request button | control test | verified |
| Manager correction history | `AttendanceCorrection` | reason required | reason field | workflow test | verified |
| Refund approval is not a transfer | `review_refund` | ceiling under lock | refund copy | workflow and concurrency approval test | verified |
| Report snapshot freeze and revision | report services | return does not edit snapshot | return and revise buttons | workflow test | verified |
| Super admin sees sent reports by default | report queryset | draft hidden | reports page | `test_super_admin_does_not_see_draft_reports_by_default` | verified |
| Privacy of classmates, photos, other centres | serializers and photo view | 403 or redaction | existing lists | `test_privacy_and_scope` | verified |
| Notifications owned and deduped | `notify` | recipient filter, unique key | bell | `test_notifications_are_deduplicated_and_private` | verified |
| Integrity checker is read-only | `integrity_report` | no saves | governance list | controlled bad rows, `updated_at` unchanged | verified |
| Room capacity edit | no route | PATCH 405; enrollment rechecks current size | not offered | `test_classroom_capacity_has_no_update_route` | out of scope, not a defect |
| Workflow screens | page components | API tests remain the authority | governance, settings, enrollment, attendance, payments, refunds, reports, notifications | 20 frontend tests | browser checks do not replace the API suite |
| Concurrency of seats, contracts, schedules, payments, refunds, waitlist, idempotency | service locks and unique keys | final row counts | payment dialog reuses one key | 10 tests passed on MariaDB 10.11 and on MySQL 8.0.46 CI | conditional unique indexes are not created; Django leaves them off for MySQL |
| Previous application writing the new schema | migrations are additive | old app can still insert an empty payment key | n/a | migration operation test forbids deletes | rollback is restore-from-backup, documented in `docs/DEPLOYMENT.md` |
