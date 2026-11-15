# Implementation status

Branch: `cursor/tuition-center-mis-3938`.

Current phase: the permission, policy, payment, privacy, and concurrency gaps from the intermediate delivery are implemented. The completion labels are in `docs/COMPLETION_MATRIX.md`.

## Verification

- SQLite: `python manage.py test apps.common.tests` — 51 tests, 10 concurrency tests skipped, OK.
- MariaDB 10.11.14 InnoDB on `127.0.0.1`, disposable database `course_tuition_center_mis_test`: `TEST_DB=mysql python manage.py test apps.common.tests` — 51 tests, OK. That includes the 10 concurrency tests.
- Django 5.2 does not install conditional unique indexes on MySQL or MariaDB (`supports_partial_indexes` is false). CI on MySQL 8.0.46 printed the same six `models.W036` warnings. Payment idempotency uses a normal unique key, which both engines install. Policy versions, permission overrides, waitlist rows, and withdrawal requests are protected by the application checks and the row locks, not by those conditional indexes.
- GitHub Actions run `43745296044` on commit `51e1f68` used MySQL 8.0.46 and finished `python manage.py test apps.common.tests` with 51 tests, OK, including the ten concurrency tests. The frontend job on that commit passed the eight tests that existed then.
- Frontend `npm test` — 20 tests, OK. They cover the governance matrix, policy display, waitlist promotion, withdrawal, attendance correction, payment retry, receipt text, refund approval, report return, a revoked prepare permission, notification ownership, sign-out, and RTL. `npm run build` completed. The main bundle is still larger than 500 kB.

## Not claimed

- The previous release is not a safe writer after these migrations. See `docs/DEPLOYMENT.md`.
- No production database was migrated.
- Conditional unique indexes are not a database guarantee on MySQL 8 or MariaDB with this Django version.
