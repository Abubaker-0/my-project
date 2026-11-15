# Tuition Center Management Information System

Phase 2 adds the weekly timetable, bulk attendance, fee plans, invoices, payments, PDF receipts, and the finance and today dashboards. It sits on the Phase 1 academic record and the Phase 0 sign-in, role permissions, branch scope, and audit trail.

Later phases add exams, payroll, and the parent portal.

## Layout

```text
backend/     FastAPI application, Alembic migrations, pytest
frontend/    React 18 + Vite application, Vitest
```

The API is mounted at `/api/v1`. Interactive docs are at `http://127.0.0.1:8000/docs` after the API is running.

## Phase 0 decisions

- Routers validate and delegate. Services commit transactions. Repositories own the SQL, including branch filters.
- Users are global. A grant in `user_roles` is either tied to one branch or, when `branch_id` is null, covers every branch. A stored `branch_key` makes that single global grant unique on MariaDB, which would otherwise allow duplicate NULLs.
- Access tokens last 15 minutes and carry only the user id. Permissions are read from the database on each request, so a role edit applies immediately. Refresh tokens are random, stored as SHA-256 hashes, and rotated. Reusing an old refresh token revokes that session family.
- The browser keeps the access token in memory and sends the refresh token as an HttpOnly cookie scoped to `/api/v1/auth`. The JSON login response also includes the refresh token for scripts and tests. The web app does not store it.
- Business audit rows (login, create, update, delete, permission changes, password changes) are written by the service inside the same transaction. Middleware only attaches the request id, client IP, and user agent. `X-Forwarded-For` is ignored unless `TRUST_PROXY=true`.
- Passwords use argon2. Five failures lock the account for 15 minutes. Login and reset routes are rate limited per IP in the API process.
- Money columns use `DECIMAL(12,2)` and are returned as strings with two decimal places. The helper is `app.db.types.MONEY`.
- The seed loads permissions, the eight system roles, the Main Campus branch, and one super admin. Outside production it also loads the 2026-2027 year, four courses, four batches, 30 students (`MAIN-2026-0001` onward), and the teacher `maya.iqbal@tuition.example` / `Teacher@12345`. A second seed skips that sample once the first admission number exists. The operations sample is separate: it adds a weekly timetable, the fee plan "Monthly tuition", three invoices (`MAIN-INV-0001` overdue, `MAIN-INV-0002` partial, `MAIN-INV-0003` paid), and the accountant `leila.hassan@tuition.example` / `Account@12345`. It skips the fee plan when that name already exists, and still adds a Sunday Math slot through 31 December 2026 when that slot is missing. System roles other than Super Admin are not rewritten on a later seed.

## XAMPP on Windows

Apache is not required. Start **MySQL** only.

1. Install [XAMPP](https://www.apachefriends.org/) and start MySQL from the XAMPP Control Panel.
2. Open phpMyAdmin at `http://localhost/phpmyadmin` and run:

```sql
CREATE DATABASE tuition_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tuition_app'@'localhost' IDENTIFIED BY 'change_me_strong';
GRANT ALL PRIVILEGES ON tuition_db.* TO 'tuition_app'@'localhost';
FLUSH PRIVILEGES;
```

Use a stronger password than the sample. The application user should not be XAMPP's `root` account outside your own machine. MariaDB 10.4 or newer is enough. The schema avoids MySQL-8-only features.

3. Install Python 3.11 or newer and Node.js 20 or newer.

### API

From `backend` in PowerShell:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```

Edit `.env` if the database password differs. Then:

```powershell
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

The seed account is `admin@tuition.example`. The password is `SEED_ADMIN_PASSWORD` in `.env` (the example value is `Admin@12345`). Change it after the first sign-in. Running the seed again does not reset that password. It does grant Super Admin any new permission codes.

In development, password-reset messages are appended to `backend/var/mail.log`. SMTP is added with notifications.

### Web app

From `frontend`:

```powershell
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://127.0.0.1:8000`, so the refresh cookie stays on the page origin.

## Tests and checks

API, from `backend`:

```powershell
ruff check app tests alembic
black --check app tests alembic
pytest
```

Web, from `frontend`:

```powershell
npm test
npm run lint
npm run build
```

Pytest uses SQLite so it does not need MySQL. `alembic upgrade head` is the check that the migration runs on MariaDB.

## Phase 1 rules

- An open enrollment is `active` while the batch has a free seat, otherwise `waitlisted` with the next position. Withdrawing an active seat promotes the earliest waitlisted student when the batch is still planned or active. Two open seats for the same student in one batch are rejected by a generated column.
- A teacher sees students and enrollments only for assigned batches. A parent sees only linked children. Those limits are a union when one account has both roles.
- An inquiry becomes `converted` only through `POST /inquiries/{id}/convert`. A lost lead has to be reopened first.
- Student documents stay on local disk under `UPLOAD_DIR` (default `backend/var/uploads`), at most 5 MB, and only PDF, JPEG, PNG, or WebP.
- Changing a student's campus withdraws open seats. A guardian moves with the student only when that guardian has no other child still at the old campus.

## Phase 2 rules

- A class session needs a room or a teacher, and both must belong to the batch's campus. The teacher must already be assigned to that batch. Sessions are allowed only on planned or active batches. Weekdays are Monday `0` through Sunday `6`.
- The same room or the same teacher cannot hold two scheduled sessions whose dates and times overlap. Touching boundaries (`10:00` after a slot that ends at `10:00`) are allowed. Cancelling a session keeps the row and frees the room and the teacher. Overlap is checked in the application with row locks; MariaDB has no exclusion constraints.
- Attendance is one sheet per batch and date. Marks are saved in bulk and only for students with an active seat. Omitted students keep their previous mark. A teacher who is not assigned to the batch gets the same not-found response as a missing batch.
- An invoice balance is `total − sum(completed payments)`. Status becomes `paid` when the balance is zero, `partial` when some of it is paid, `issued` when nothing is paid and the due date is still ahead, and `overdue` when nothing is paid and the due date has passed. A partial invoice stays `partial` after the due date; the finance dashboard still counts that remaining balance as overdue money.
- Invoices and payments are never hard-deleted. Cancel an invoice with a reason only after every completed payment is voided. A voided payment stays on the invoice. A fee plan can be removed only when no invoice uses it.
- `POST /payments` requires an `Idempotency-Key` header of 8–80 characters. The same key and the same invoice, amount, and method return the original payment. The same key with a different body returns `409 IDEMPOTENCY_CONFLICT`. `GET /payments/{id}/receipt` returns a one-page PDF.

## API surface

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/api/v1/health` | public |
| POST | `/api/v1/auth/login` | public, rate limited |
| POST | `/api/v1/auth/refresh` | refresh token |
| POST | `/api/v1/auth/logout` | refresh token |
| POST | `/api/v1/auth/logout-all` | signed in |
| GET | `/api/v1/auth/me` | signed in |
| GET | `/api/v1/auth/sessions` | signed in |
| POST | `/api/v1/auth/forgot-password` | public, rate limited |
| POST | `/api/v1/auth/reset-password` | public, rate limited |
| POST | `/api/v1/auth/change-password` | signed in |
| GET, POST | `/api/v1/users` | `users:read`, `users:create` |
| GET, PATCH, DELETE | `/api/v1/users/{id}` | `users:read`, `users:update`, `users:delete` |
| POST | `/api/v1/users/{id}/restore` | `users:update`, Super Admin only |
| GET | `/api/v1/roles` | `roles:read` |
| POST | `/api/v1/roles` | `roles:create` |
| PUT | `/api/v1/roles/{id}/permissions` | `permissions:assign` |
| DELETE | `/api/v1/roles/{id}` | `roles:delete` |
| GET | `/api/v1/permissions` | `permissions:read` |
| GET, POST | `/api/v1/branches` | `branches:read`, `branches:create` |
| GET, PATCH, DELETE | `/api/v1/branches/{id}` | `branches:read`, `branches:update`, `branches:delete` |
| GET, POST | `/api/v1/academic-years` | `academic_years:read`, `academic_years:create` |
| GET, PATCH, DELETE | `/api/v1/academic-years/{id}` | `academic_years:read`, `academic_years:update`, `academic_years:delete` |
| POST | `/api/v1/academic-years/{id}/terms` | `academic_years:update` |
| GET, POST | `/api/v1/rooms` | `rooms:read`, `rooms:create` |
| GET, PATCH, DELETE | `/api/v1/rooms/{id}` | `rooms:read`, `rooms:update`, `rooms:delete` |
| GET, POST | `/api/v1/subjects` | `subjects:read`, `subjects:create` |
| PATCH, DELETE | `/api/v1/subjects/{id}` | `subjects:update`, `subjects:delete` |
| GET, POST | `/api/v1/courses` | `courses:read`, `courses:create` |
| GET, PATCH, DELETE | `/api/v1/courses/{id}` | `courses:read`, `courses:update`, `courses:delete` |
| GET, POST | `/api/v1/batches` | `batches:read`, `batches:create` |
| GET, PATCH, DELETE | `/api/v1/batches/{id}` | `batches:read`, `batches:update`, `batches:delete` |
| POST | `/api/v1/batches/{id}/teachers` | `batches:update` |
| GET, POST | `/api/v1/students` | `students:read`, `students:create` |
| GET, PATCH, DELETE | `/api/v1/students/{id}` | `students:read`, `students:update`, `students:delete` |
| POST | `/api/v1/students/{id}/guardians` | `students:update` |
| POST | `/api/v1/students/{id}/documents` | `documents:create` |
| GET, POST | `/api/v1/inquiries` | `inquiries:read`, `inquiries:create` |
| GET, PATCH, DELETE | `/api/v1/inquiries/{id}` | `inquiries:read`, `inquiries:update`, `inquiries:delete` |
| POST | `/api/v1/inquiries/{id}/followups` | `inquiries:update` |
| POST | `/api/v1/inquiries/{id}/convert` | `inquiries:convert` |
| GET, POST | `/api/v1/enrollments` | `enrollment:read`, `enrollment:create` |
| POST | `/api/v1/enrollments/{id}/withdraw` | `enrollment:withdraw` |
| POST | `/api/v1/enrollments/{id}/transfer` | `enrollment:transfer` |
| POST | `/api/v1/enrollments/{id}/complete` | `enrollment:update` |
| GET | `/api/v1/audit-logs` | `audit:read` |
| GET, POST | `/api/v1/timetable/sessions` | `timetable:read`, `timetable:create` |
| PATCH | `/api/v1/timetable/sessions/{id}` | `timetable:update` |
| POST | `/api/v1/timetable/sessions/{id}/cancel` | `timetable:delete` |
| GET | `/api/v1/attendance/sheets` | `attendance:read` |
| PUT | `/api/v1/attendance/sheets` | `attendance:mark` |
| GET, POST | `/api/v1/fee-plans` | `fees:read`, `fees:create` |
| GET, PATCH, DELETE | `/api/v1/fee-plans/{id}` | `fees:read`, `fees:update`, `fees:delete` |
| GET, POST | `/api/v1/invoices` | `invoices:read`, `invoices:create` |
| GET | `/api/v1/invoices/{id}` | `invoices:read` |
| POST | `/api/v1/invoices/{id}/cancel` | `invoices:cancel` |
| POST | `/api/v1/payments` | `payments:create`, `Idempotency-Key` header |
| POST | `/api/v1/payments/{id}/void` | `payments:void` |
| GET | `/api/v1/payments/{id}/receipt` | `payments:read` |
| GET | `/api/v1/dashboard/finance` | `reports:read` |
| GET | `/api/v1/dashboard/today` | `timetable:read` |

Lists accept `page`, `page_size` (max 100), `sort` (prefix `-` for descending), and `q`. Errors use `{ "code", "message", "details" }`. Send `X-Branch-Id` to narrow a list to one campus you already can access. The branch list itself ignores that header so the switcher can still show every campus you may pick.

## What is next

Phase 3: assessments, marks that cannot exceed the assessment maximum, published results that stay locked until a coordinator reopens them, and the teacher gradebook.
