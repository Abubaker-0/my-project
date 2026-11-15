# Implementation status

Branch: `cursor/tuition-center-mis-3938`.

Current phase: workflow controls and the requested enhancement areas are in the repository. Verification so far is the Django test suite on SQLite plus the frontend unit tests. MySQL lock behavior has not been executed in this environment.

## Completed

- Five role workflows remain on the existing services: center lifecycle, staff contracts, courses and enrollment, attendance, cash and bank payments, scholarships, refunds, and official reports.
- Contract eligibility now requires an active status and an Asia/Kabul date inside the contract.
- Permission catalog, global and center restrictions, and effective-permission explanation.
- Policy revisions for global and center settings.
- In-app notifications and `notify_contract_expirations`.
- Payment idempotency and an authorized receipt that states it is not a bank transfer.
- Waitlist, manager promotion, withdrawal requests, and completion after the course end date.
- Report return, linked revision, frozen prior snapshot, and super admin default of sent reports.
- Invoice CSV export gated by `exports.invoices`.
- Read-only `check_integrity` command and `/api/reports/integrity/`.
- Frontend paths for correction reasons, waitlist, withdrawal, promotion, completion, receipts, report return and revise, notifications, and a super admin governance page.
- Migrations: `attendance`, `centers`, `common`, `enrollments`, `finance`, and `reports` `0002_workflow_controls`.

## Verification recorded

- `DB_ENGINE=sqlite python manage.py test apps.common.tests.test_business_rules apps.common.tests.test_workflows` — 24 tests, OK, on SQLite.
- `python manage.py makemigrations --check --dry-run` with `DB_ENGINE=sqlite` — no model changes left unmigrated.
- Frontend `npm test` — 5 tests, OK.
- Frontend `npm run build` — production build completed. Vite warned that the main bundle is larger than 500 kB.
- Local SQLite development database received the six `0002_workflow_controls` migrations. `check_integrity` reported no issues. `notify_contract_expirations` ran twice and created no duplicate notices.
- Browser pass against the running app: super admin governance and prospective policy copy, manager waitlist and withdrawal panels, refund wording, finance receipt statement, and the student course page. A mobile-width governance view rendered. The temporary export restriction used during that click was removed from the local database afterward.
- MySQL was not running. Transaction and lock behavior was not proven on MySQL.
- `TEST_DB=mysql` was not used.

## Remaining

- Apply `0002_workflow_controls` on the real MySQL database during a controlled deployment. This environment did not migrate an unidentified MySQL database.
- Run the suite with `TEST_DB=mysql` where MySQL is available, including two concurrent seat allocations.
- Teacher correction is a manager action with history. There is no separate teacher request object.
- Classroom capacity cannot be lowered from the API because rooms are created and listed, not patched. The enrollment transaction still refuses a seat beyond the current room capacity.
- No repair command rewrites conflicting financial history. `check_integrity` only reports it.
- External email, SMS, and bank transfer were not added.

## Environmental blockers

- MySQL on `127.0.0.1:3306` refused connections while migrations were generated. Migration files were still written. They were applied only to the disposable SQLite test database.
