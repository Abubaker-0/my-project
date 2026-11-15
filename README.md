# Tuition Center Management Information System

Phase 0 is the foundation: a FastAPI service with MariaDB, signed-in users, role permissions, an audit trail, and a React shell that keeps the access token in memory and the refresh token in an HttpOnly cookie.

Later phases add students, classes, fees, exams, payroll, and the parent portal. They sit on the same branch scope, permission checks, and audit log.

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
- Money columns, when they arrive, use `DECIMAL(12,2)`. This phase has no money yet. The helper is `app.db.types.MONEY`.
- Sample courses and the 30 sample students are not in this phase. Those tables do not exist yet. The seed loads permissions, the eight system roles, the Main Campus branch, and one super admin.

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

## API surface in this phase

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
| GET | `/api/v1/branches` | `branches:read` |
| GET | `/api/v1/audit-logs` | `audit:read` |

Lists accept `page`, `page_size` (max 100), `sort` (prefix `-` for descending), and `q`. Errors use `{ "code", "message", "details" }`. Send `X-Branch-Id` to narrow a list to one campus you already can access. The branch list itself ignores that header so the switcher can still show every campus you may pick.

## What is next

Phase 1: branches (write), academic years, rooms, students, guardians, documents, inquiries with conversion, courses, batches, and enrollment with capacity and a waitlist. That phase also seeds sample courses and 30 students.
