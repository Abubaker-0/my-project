# Course Tuition Center MIS

A tuition-center management system for super admins, center managers, finance managers, teachers, and students. It covers centers, contracts, courses, classes, enrollment, attendance, payments, installments, scholarships, refunds, and reports.

The interface is English and Dari (right to left), with a light theme and a dark theme.

## Stack

- Backend: Django, Django REST Framework, JWT
- Database: MySQL (`course_tuition_center_mis`, `utf8mb4`) through XAMPP. PyMySQL is used so a separate `mysqlclient` build is not required.
- Frontend: React, Vite, React Router, Axios, React Hook Form, Zod, i18next, Recharts

Tests run on SQLite automatically. Day-to-day use is MySQL.

## Sample logins

These accounts exist after `seed_data`. Passwords are for local demo only.

| Role | Username | Password |
| --- | --- | --- |
| Super Admin | `superadmin` | `Admin@12345` |
| Center Manager (Kabul) | `manager.kabul` | `Manager@12345` |
| Finance Manager (Kabul) | `finance.kabul` | `Finance@12345` |
| Teacher | `teacher.zahra` | `Teacher@12345` |
| Teacher | `teacher.karim` | `Teacher@12345` |
| Student | `student.ali` | `Student@12345` |
| Student | `student.maryam` | `Student@12345` |
| Student | `student.omar` | `Student@12345` |
| Center Manager (Herat) | `manager.herat` | `Manager@12345` |
| Finance Manager (Herat) | `finance.herat` | `Finance@12345` |
| Teacher (Herat) | `teacher.herat` | `Teacher@12345` |
| Student (Herat) | `student.herat` | `Student@12345` |

## Windows setup with XAMPP

1. Install [XAMPP](https://www.apachefriends.org/) and start **MySQL** from the XAMPP Control Panel.
2. Open `http://localhost/phpmyadmin`.
3. Create a database named `course_tuition_center_mis`.
4. Set the collation to `utf8mb4_unicode_ci`.
5. The default XAMPP MySQL user is `root` with an empty password, on `127.0.0.1` port `3306`. Change that before any shared machine.

Install Python 3.12 and Node.js 20 or newer.

## Backend

From the project folder:

```bat
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py create_super_admin
python manage.py seed_data
python manage.py runserver
```

On macOS or Linux, activate the virtualenv with `source .venv/bin/activate`.

The API listens on `http://127.0.0.1:8000`. Health check: `http://127.0.0.1:8000/api/health/`.

`create_super_admin` reads `SUPER_ADMIN_*` from `.env` and can be run again safely. `seed_data` skips itself when the Kabul center already exists.

Useful checks:

```bat
python manage.py test apps.common.tests.test_business_rules
```

Set `TEST_DB=mysql` only when you want the test suite to use MySQL. The default test database is SQLite.

## Frontend

In a second terminal:

```bat
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`. `VITE_API_URL` must be `http://localhost:8000/api` with no trailing slash.

The language switch and theme switch are on the sign-in page and in the top bar. The choice is kept in the browser (`ctcms-lang`, `ctcms-theme`). Dari switches the layout to right-to-left.

## What each role can do

- **Super Admin** sees every center, its people, courses, finance figures, and reports. They create centers and assign the single center manager. They do not create courses, classes, schedules, or enrollments.
- **Center Manager** works only inside their center: courses, classes, people, contracts, manual enrollment, attendance corrections, and sending finance reports upward.
- **Finance Manager** records cash and bank payments, up to three installments, scholarships, and refund requests for their center. They cannot approve a refund.
- **Teacher** sees assigned classes, marks present or absent, and reads their contract. They cannot edit a register after submitting it.
- **Student** sees courses in their own center, enrolls when the course is open and has seats, and reads their attendance, invoices, installments, and scholarships.

A person cannot be active in two centers at once. The manager picker hides managers who already hold an active contract.

## Project layout

```
backend/config          Django settings and root URLs
backend/apps/accounts   Users, JWT, profiles, contracts
backend/apps/centers    Centers and settings
backend/apps/courses    Courses
backend/apps/classes    Classes, rooms, schedules
backend/apps/enrollments
backend/apps/attendance
backend/apps/finance    Invoices, payments, installments, scholarships, refunds
backend/apps/reports    Dashboards and official reports
backend/apps/common     Shared rules, audit log, API envelope
frontend/src            React application
docs                    API, permissions, and business rules
```

## API shape

Successful JSON:

```json
{ "success": true, "message": "OK", "data": {} }
```

Failed JSON:

```json
{ "success": false, "message": "Why it failed", "errors": {} }
```

Send `Authorization: Bearer <access>` on every call except login, refresh, and password reset. Lists are paginated with `page` and `page_size` (default 10, maximum 100) and support `search` and `ordering` where the endpoint documents them.

More detail is in [docs/API.md](docs/API.md), [docs/PERMISSIONS.md](docs/PERMISSIONS.md), and [docs/BUSINESS_RULES.md](docs/BUSINESS_RULES.md).

## Production notes

- Set `DJANGO_DEBUG=False`, a long `DJANGO_SECRET_KEY`, and the real host in `DJANGO_ALLOWED_HOSTS`.
- Give MySQL its own user. Do not ship the demo passwords.
- Serve the frontend build (`npm run build`) behind the same site or keep `CORS_ALLOWED_ORIGINS` limited to that origin.
- Profile photos and center logos are downloaded with the JWT. They are not public media URLs.
