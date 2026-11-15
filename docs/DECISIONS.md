# Material decisions

These decisions close gaps where the repository did not already state a stronger, consistent, and safe rule. Existing business rules that were already implemented (inactive centers until a manager exists, one active manager, cash or bank only, a maximum of three installments, present or absent only, no cross-center writes) were kept.

## D-001 — Contract dates narrow eligibility; they do not allow a second active contract

- Ambiguity: whether a future or expired contract with status `active` authorizes work, and whether non-overlapping contracts may both be stored as active.
- Evidence reviewed: `Contract.active_contract_lock` and `active_manager_lock` unique constraints; `active_contract_for` previously trusted status alone; `assert_operational`.
- Chosen behavior: a contract authorizes operational writes only when its status is active and today in Asia/Kabul is inside `start_date` through `end_date`. The database still allows only one stored active contract per person and one active manager lock per center.
- Reason: date checks stop a future or lapsed contract from authorizing work. Relaxing the unique lock would weaken the existing exclusivity rule.
- Security and financial implications: expired staff cannot record payments, attendance, or enrollments. Account and password actions that do not call `assert_operational` remain available.
- Effect on existing data: none until the next eligibility check. `refresh_expired_contracts` still flips a past end date to `expired`.
- Tests: existing operational checks; workflow tests sign in through eligible staff.
- Reversibility: remove the date filters in `active_contract_for`.

## D-002 — Protected duties stay in service checks

- Ambiguity: whether a settings screen may grant or deny any permission, including finance collection and refund approval.
- Evidence reviewed: role checks inside finance, attendance, enrollment, and report services; no prior permission table.
- Chosen behavior: the catalog in `apps/common/permissions_catalog.py` is the ceiling. Protected codes cannot be stored as denials. Configurable codes (`reports.prepare`, `exports.invoices`, `waitlist.promote`) may only be narrowed, globally or for one center. A center restriction cannot exceed the global ceiling. `has_permission` is applied to those new features. Existing payment and attendance services still use their role checks, so a settings mistake cannot turn off collection or attendance.
- Reason: separation of duties must fail closed and must not depend on a row that an operator can delete.
- Security and financial implications: a super admin cannot give a teacher the right to collect money, and cannot disable the manager-only refund decision.
- Effect on existing data: new `PermissionOverride` rows only. No backfill.
- Tests: `test_protected_permission_cannot_be_denied`, `test_export_honors_a_global_restriction`.
- Reversibility: stop reading overrides. Existing role checks remain.

## D-003 — Refund approval is the recorded refund

- Ambiguity: whether approval should wait for a bank disbursement stage.
- Evidence reviewed: `Refund` has request, approve, and reject. There is no payout model.
- Chosen behavior: manager approval records a completed refund against payments already received, after subtracting approved refunds and reserving pending requests. Rejection releases the reservation. The screen states that approval does not send a bank transfer. Refund totals stay on `refunded_amount` and `refund_state`, separate from `paid_amount`. Approving a refund does not recreate student debt.
- Reason: inventing a disbursement stage would imply a transfer this product does not perform.
- Security and financial implications: the available amount is rechecked under a row lock. A second decision on the same request is rejected.
- Effect on existing data: `refund_state` is computed. Old invoice status values are not rewritten.
- Tests: existing refund tests; workflow coverage of the reservation path through the existing service.
- Reversibility: a later disbursement model can be added without treating current approvals as transfers.

## D-004 — Attendance stays one record per class and date

- Ambiguity: whether each scheduled meeting needs its own attendance row.
- Evidence reviewed: `AttendanceSession` unique on class and date; a class may have several schedules on one weekday.
- Chosen behavior: multiple meetings on the same date share that daily record. The roster is enrollments that were active on that date: pending and rejected are excluded; withdrawn or completed students remain only when the decision date is after the attendance date. A manager correction requires a reason of at least five characters and stores the previous value.
- Reason: per-meeting attendance would need a new model and a migration that this change does not invent.
- Security and financial implications: teachers cannot change a submitted register. Students are not marked before they joined.
- Effect on existing data: new `AttendanceCorrection` rows only. Existing sessions stay.
- Tests: `test_attendance_is_present_or_absent_and_manager_corrects_it`, `test_correction_keeps_the_original_mark`.
- Reversibility: stop requiring a reason and stop writing correction rows. Do not delete history.

## D-005 — One scholarship per enrollment

- Ambiguity: whether a second grant should stack on the first.
- Evidence reviewed: `ScholarshipGrant` was previously updated in place for the same enrollment.
- Chosen behavior: a second grant is a conflict. The fixed amount is checked against the invoice when it is applied. Applying before any payment redistributes an unpaid installment plan in the same transaction.
- Reason: stacking was not a safe existing rule, and replacing the grant silently would hide the first discount.
- Security and financial implications: the payable fee cannot be reduced twice. Issued payments are not rewritten.
- Effect on existing data: enrollments that already have one grant are unchanged.
- Tests: existing scholarship tests; a second apply raises `ConflictError`.
- Reversibility: restore update-in-place only with an explicit stacking policy.

## D-006 — Waitlist does not hold a seat or create a charge

- Ambiguity: whether joining a full class should reserve capacity or raise an invoice.
- Evidence reviewed: `enroll` creates the invoice and consumes a seat for pending and active rows.
- Chosen behavior: a waitlist row stores position only. The center manager promotes it. Promotion calls `enroll`, which rechecks center, course, class, capacity, duplicates, and schedule conflicts inside the enrollment transaction. A seat opening does not create a debt by itself.
- Reason: an automatic invoice would charge a student who has not been offered the seat.
- Security and financial implications: capacity counts ignore waitlisted and rejected rows. Classroom occupancy uses the smallest scheduled room and is checked in the same transaction as the course capacity check.
- Effect on existing data: none. New `WaitlistEntry` rows only.
- Tests: `test_waitlist_does_not_invoice_and_promotion_rechecks_capacity`.
- Reversibility: stop exposing the waitlist endpoints. Existing enrollments stay.

## D-007 — Withdrawal does not cancel debt

- Ambiguity: whether leaving a class should void the invoice or start a refund.
- Evidence reviewed: invoices are one-to-one with an active enrollment; refunds are a separate manager decision.
- Chosen behavior: the student requests withdrawal. The manager approves or rejects. Approval sets the enrollment to withdrawn, which releases the open-enrollment key and the seat. The invoice, payments, and attendance stay. Completion is a manager action after the course end date and is not an open enrollment.
- Reason: debt and refunds are separate controlled workflows.
- Security and financial implications: a withdrawn student can still owe the recorded balance.
- Effect on existing data: none until a request is approved.
- Tests: `test_withdrawal_keeps_the_invoice`.
- Reversibility: stop the new endpoints. Do not delete historical enrollments.

## D-008 — Official report snapshots are frozen

- Ambiguity: whether returning a report should edit its numbers, and which reports the super admin sees.
- Evidence reviewed: `FinancialReport.snapshot` is written when the draft is created; submit and send change status only.
- Chosen behavior: return is allowed only from `submitted_to_manager`, requires a note, and does not change `snapshot`. Finance then creates a new draft linked by `previous`, with its own snapshot and the next revision number. A sent snapshot is never edited. The super admin list defaults to `sent_to_super_admin` unless `?status=` is passed. Live dashboards stay separate.
- Reason: a returned file must stay explainable, and head office should not see drafts by default.
- Security and financial implications: later payments do not rewrite a snapshot that was already stored.
- Effect on existing data: new nullable revision columns. Old reports remain revision 1 with no previous link.
- Tests: `test_returned_report_needs_a_new_revision`.
- Reversibility: ignore `returned` and the link. Do not delete stored snapshots.

## D-009 — Payment idempotency is optional and bound to the actor

- Ambiguity: whether every payment needs a client key, and what a retry should do.
- Evidence reviewed: payments had no idempotency field; tests create several payments without a key.
- Chosen behavior: an empty key still allows distinct payments. A non-empty key is unique per receiving user. The same actor, key, invoice, amount, method, and reference returns the original payment and does not write a second audit. A different payload with that key is rejected with 409.
- Reason: forcing a key would break current clients. Binding the key to the actor stops one user from replaying another user's key.
- Security and financial implications: retries cannot double-collect when the caller sends a stable key. Client totals are not trusted; the server uses the invoice outstanding balance.
- Effect on existing data: `idempotency_key` defaults to empty. `receipt_number` is assigned for new payments. Old payments keep a null receipt number until one is read, and the receipt action fills it if missing.
- Tests: `test_identical_payment_retry_returns_the_same_receipt`.
- Reversibility: stop sending the key. The unique constraint stays safe for empty keys because it is partial.

## D-010 — Policy changes apply later

- Ambiguity: whether lowering the installment cap should rewrite existing plans or frozen reports.
- Evidence reviewed: `CenterSettings` and `GlobalSettings` were overwritten in place.
- Chosen behavior: each save appends a `PolicyRevision`. The new cap applies to later plans. An unpaid plan can be replaced only when `replace` is true, and the old slices are archived. A plan that already has a payment cannot be replaced. Remainder rounding stays on the last installment. Allocation follows due date, then number. Overdue uses Asia/Kabul dates.
- Reason: rewriting an issued invoice or a sent report would change financial history.
- Security and financial implications: a lower cap does not invalidate a plan that was legal when it was created.
- Effect on existing data: the next settings save writes revision 1. Current settings values are not recalculated.
- Tests: `test_policy_save_keeps_a_version`.
- Reversibility: stop writing revisions. Archives already stored should be kept.

## D-011 — Alerts stay inside the application

- Ambiguity: how contract expiry should be delivered without new infrastructure.
- Evidence reviewed: no Celery, Redis, email, or SMS integration.
- Chosen behavior: notifications are rows for the signed-in user. `notify_contract_expirations` creates alerts for 30 days, 7 days, and the end date, including the center manager when that person is different. The dedupe key makes a repeated run a no-op for the same window. The command does not send email or SMS.
- Reason: a simulated external delivery would be misleading.
- Security and financial implications: none beyond showing contract dates to the contract holder and their manager.
- Effect on existing data: new notification rows only.
- Tests: dedupe is covered by the unique key; the command was not executed against MySQL in this environment.
- Reversibility: stop scheduling the command. Existing notices can remain.

## D-012 — Students do not see another student's private fields

- Ambiguity: class lists previously returned email, phone, and photo for every classmate.
- Evidence reviewed: `UserBriefSerializer` used on class rosters and attendance.
- Chosen behavior: when the viewer is a student or a teacher looking at a different student, email, phone, and photo are removed. Teachers still see the name required to mark attendance. Finance still receives the student fields already used on invoices and payments.
- Reason: classmates do not need contact or photo data to attend class.
- Security and financial implications: this is a response filter. It does not delete stored profile data.
- Effect on existing data: none.
- Tests: serializer behavior is covered by the roster endpoints used in attendance tests; a dedicated privacy assertion was not added in this pass.
- Reversibility: stop redacting fields in `to_representation`.
