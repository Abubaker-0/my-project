# Deployment and rollback

No production migration is authorized by the application change itself. Apply these steps only on a database you have chosen.

## Before deployment

1. Take a backup of `course_tuition_center_mis`.
2. Put the site in maintenance mode. Stop payment, enrollment, and report writes.
3. Confirm the database is MySQL 8. CI uses MySQL 8.0. A local MariaDB 10.11 run passed the same suite, but MariaDB does not install partial unique indexes (`models.W036`). Payment idempotency uses a normal unique key and is enforced on both. Policy, permission, waitlist, and withdrawal partial uniques are enforced by MySQL 8 and by the application checks.
4. Confirm `TIME_ZONE` is `Asia/Kabul`.
5. Run `python manage.py migrate` and `python manage.py check`.
6. Run `python manage.py check_integrity` and read the output. It does not change rows.

## After deployment

1. Sign in as each of the five roles and open one page that role owns.
2. Record one payment in a disposable centre with an idempotency key, then submit the same key again. The second response is the same payment.
3. Confirm global currency remains `AFN`.
4. Run `python manage.py notify_contract_expirations` once, then again. The second run must not add a second copy of the same alert.
5. Schedule that command once a day. It writes in-app notices only.

## Rollback

The `0002` and `0003` migrations add tables and nullable or defaulted columns. They do not delete financial rows.

Do not drop those tables to roll back. They can hold receipts, permission history, policy revisions, correction requests, and report links.

The previous application is not a safe writer against this schema:

- It can insert a payment with an empty idempotency key. The new API rejects that. Leaving the old application running allows a second financial effect.
- It does not know `returned` report status, waitlist rows, or permission versions.

Roll back by restoring the database backup taken before migrate, then deploying the previous release. If new financial or audit rows were written after migrate, do not restore over them. Keep the new release in place and fix forward.

## Local MariaDB note

The disposable server used for verification was MariaDB 10.11.14 on `127.0.0.1:3306`, database `course_tuition_center_mis_test`, user `mis`. It was created for tests and is not a production database. MySQL 8.0 is the engine in `.github/workflows/tests.yml` and was not started on this machine.
