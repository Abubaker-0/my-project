# Implementation status

Branch: `cursor/tuition-center-mis-3938`.

Current phase: the permission, policy, payment, privacy, and concurrency gaps from the intermediate delivery are implemented. The completion labels are in `docs/COMPLETION_MATRIX.md`.

## Verification

- SQLite: `python manage.py test apps.common.tests.test_business_rules apps.common.tests.test_workflows apps.common.tests.test_controls` — 41 tests, OK. The 10 concurrency tests skip on SQLite.
- MariaDB 10.11.14 InnoDB on `127.0.0.1`, disposable database `course_tuition_center_mis_test`: `TEST_DB=mysql python manage.py test apps.common.tests` — 51 tests, OK. That includes the 10 concurrency tests.
- MariaDB warned that partial unique constraints are not installed (`models.W036`). Payment idempotency uses a normal unique key, which MariaDB did install. The other partial uniques are installed on MySQL 8.
- MySQL 8.0 was not started in this environment. `.github/workflows/tests.yml` runs the suite against the `mysql:8.0` service.
- Frontend `npm test` — 20 tests, OK. They cover the governance matrix, policy display, waitlist promotion, withdrawal, attendance correction, payment retry, receipt text, refund approval, report return, a revoked prepare permission, notification ownership, sign-out, and RTL. `npm run build` completed. The main bundle is still larger than 500 kB.

## Not claimed

- MySQL 8.0 lock behavior was not executed here. MariaDB 10.11 InnoDB was.
- The previous release is not a safe writer after these migrations. See `docs/DEPLOYMENT.md`.
- No production database was migrated.
