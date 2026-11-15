# API

Base URL: `http://localhost:8000/api`

Authentication is JWT. `POST /auth/login/` accepts `username` (a username or an email) and `password`, and returns `access`, `refresh`, and `user`. `POST /auth/refresh/` rotates the refresh token. `POST /auth/logout/` blacklists it.

Every JSON response uses the envelope described in the README. File downloads (`/profile/photo/<id>/` and `/centers/<id>/logo/`) return the image bytes and require the bearer token.

Lists accept `search`, `ordering`, `page`, and `page_size`.

## Auth and profile

| Method | Path | Who |
| --- | --- | --- |
| POST | `/auth/login/` | Public, throttled |
| POST | `/auth/refresh/` | Public |
| POST | `/auth/logout/` | Signed in, body `{ refresh }` |
| GET | `/auth/me/` | Signed in |
| POST | `/auth/change-password/` | Signed in, `{ old_password, new_password }` |
| POST | `/auth/forgot-password/` | Public, `{ login }` |
| POST | `/auth/reset-password/` | Public, `{ token, new_password }` |
| GET, PATCH | `/profile/` | Signed in |
| POST | `/profile/photo/` | Signed in, multipart field `photo` |
| GET | `/profile/photo/<user_id>/` | Same person, same center, or super admin |

## Users and contracts

| Method | Path | Who |
| --- | --- | --- |
| GET, POST | `/users/` | Super admin creates center managers. A center manager creates finance managers, teachers, and students. |
| PATCH | `/users/<id>/` | Super admin edits managers. A manager edits other people in the center. |
| POST | `/users/<id>/activate/` and `/deactivate/` | Same editors |
| POST | `/users/<id>/role/` | Center manager. Body `{ role }` is `finance_manager`, `teacher`, or `student`, and only when no contract or enrollment is open. |
| GET | `/users/available-managers/` | Super admin. Managers with no active contract. |
| GET, POST | `/contracts/` | Manager creates a contract for a teacher or finance manager. Body is the contract fields plus `user`. |
| POST | `/contracts/<id>/terminate/` | Manager of that center, or super admin for a manager contract through replacement. |

A staff create body includes `contract` with `contract_type` (`yearly` or `six_months`), `start_date`, `end_date`, `salary_type` (`hourly` or `monthly`), `salary_amount`, and `payment_method` (`cash` or `bank`).

## Centers

| Method | Path | Who |
| --- | --- | --- |
| GET, POST, PATCH | `/centers/` | Super admin writes. Managers read their center. |
| POST | `/centers/<id>/activate/`, `/deactivate/`, `/archive/` | Super admin |
| POST | `/centers/<id>/assign-manager/` | Super admin. `{ manager_id, replace, contract }` |
| GET | `/centers/<id>/statistics/` | Super admin, manager, finance |
| GET, PATCH | `/centers/<id>/settings/` | Read: those three roles. Write: center manager. |
| GET, POST | `/centers/<id>/logo/` | Logo download or multipart `logo` |
| GET, PATCH | `/settings/global/` | Super admin |

Center settings: `allow_self_enrollment`, `require_enrollment_approval`, `max_installments` (1–3).

## Courses, classes, enrollment

| Method | Path | Who |
| --- | --- | --- |
| GET | `/courses/` | Scoped by role. Students can pass `available=1`. |
| POST, PATCH | `/courses/` | Center manager only. Create includes `schedules: [{ day_of_week, start_time, end_time, classroom }]`. |
| POST | `/courses/<id>/activate/`, `/deactivate/` | Center manager |
| GET, POST | `/classes/` | Manager creates. Teachers see their sections. Students see sections they joined. |
| GET | `/classes/<id>/students/` | People who can see the class |
| POST | `/classes/<id>/schedules/` | Manager adds one meeting |
| DELETE | `/classes/schedules/<id>/` | Manager. A class must keep one meeting. |
| GET, POST | `/classes/classrooms/` | Manager creates `{ name, capacity }` |
| GET | `/enrollments/` | Scoped |
| POST | `/enrollments/self-enroll/` | Student `{ course_id, class_id }` |
| POST | `/enrollments/manual/` | Manager `{ student_id, course_id, class_id }` |
| POST | `/enrollments/<id>/approve/`, `/reject/` | Manager, pending rows only |

`day_of_week` is 0 for Monday through 6 for Sunday.

## Attendance

| Method | Path | Who |
| --- | --- | --- |
| GET | `/attendance/` | Sessions the caller may see |
| GET | `/attendance/roster/?class_id=&date=` | Teacher of the class, or the manager |
| POST | `/attendance/mark/` | Teacher. `{ class_id, date, records: [{ student_id, status }] }`. Status is `present` or `absent`, and the roster must be complete. |
| PATCH | `/attendance/records/<id>/` | Center manager `{ status }` |
| GET | `/attendance/my/` | Student history, or the teacher's marks |
| GET | `/attendance/summary/` | Present, absent, and rate |

## Finance

| Method | Path | Who |
| --- | --- | --- |
| GET | `/finance/summary/?center=` | Finance and manager use their center. Super admin must pass `center`. Optional `start` and `end`. |
| GET | `/finance/invoices/` | Scoped. Students see their own. |
| GET, POST | `/finance/payments/` | Finance creates `{ invoice, amount, method, reference, idempotency_key }`. Bank needs a reference of at least 3 characters. The same user, key, and payload returns the original payment. A different payload with that key is `409`. |
| GET | `/finance/installments/` | Scoped |
| POST | `/finance/installments/plan/` | Finance. `{ invoice, installments: [{ due_date, amount }], replace }`. `replace` archives an unpaid plan. A plan that already has a payment cannot be replaced. |
| GET, POST | `/finance/scholarships/` | Finance creates `{ name, scholarship_type, value, description }`. `scholarship_type` is `percentage` or `fixed`. |
| POST | `/finance/scholarships/apply/` | Finance `{ scholarship, enrollment }` before any payment. |
| GET, POST | `/finance/refunds/` | Student or finance `{ invoice, amount, reason }` |
| POST | `/finance/refunds/<id>/approve/`, `/reject/` | Center manager `{ decision_note }`. Approval records the refund in the centre accounts. It does not send a bank transfer. |
| GET | `/finance/payments/<id>/receipt/` | People who can see the payment. The statement says it is not a bank transfer. |

## Reports

| Method | Path | Who |
| --- | --- | --- |
| GET | `/reports/dashboard/` | Signed in. Payload matches the role. |
| GET, POST | `/reports/financial/` | Finance creates `{ title, period_start, period_end }`. |
| POST | `/reports/financial/<id>/submit/` | Finance, draft only |
| POST | `/reports/financial/<id>/send/` | Manager, after submit |
| GET | `/reports/audit-logs/` | Super admin, or the manager for their center |
| POST | `/reports/financial/<id>/return/` | Manager, submitted reports only. `{ note }` of at least 5 characters. The snapshot is not edited. |
| POST | `/reports/financial/<id>/revise/` | Finance, from a returned report. Creates a new draft linked to the previous revision. |
| GET | `/reports/integrity/` | Super admin. Read only. |
| GET | `/reports/export/invoices/` | Super admin, manager, or finance, unless `exports.invoices` is restricted. CSV for invoices in scope. |

The super admin financial-report list defaults to reports already sent. Pass `?status=` to see another state.

## Governance

| Method | Path | Who |
| --- | --- | --- |
| GET | `/permissions/catalog/` | Super admin and center manager |
| GET | `/permissions/effective/` | Signed in. Optional `center` for the super admin. |
| GET, POST | `/permissions/overrides/` | Super admin, or a manager for their own center. Protected duties cannot be denied. Body `{ role, code, allowed, center }`. |
| GET | `/notifications/` | Signed in. Own notices only. |
| POST | `/notifications/read-all/` and `/notifications/<id>/read/` | The recipient |
| GET | `/settings/global/history/` and `/centers/<id>/settings/history/` | People who can read those settings |
| GET | `/settings/effective/?center=` | Signed in for their center. Super admin passes `center`. |

## Enrollment controls

| Method | Path | Who |
| --- | --- | --- |
| GET, POST | `/enrollments/waitlist/` | Student joins `{ course_id, class_id }`. No invoice and no reserved seat. |
| POST | `/enrollments/promote-waitlist/` | Manager `{ id }`. Rechecks capacity and eligibility. |
| POST | `/enrollments/<id>/withdraw/` | Student `{ reason }` |
| GET | `/enrollments/withdrawals/` | Student, manager, or super admin, in scope |
| POST | `/enrollments/decide-withdrawal/` | Manager `{ id, approve, note }`. Approval does not cancel the invoice. |
| POST | `/enrollments/<id>/complete/` | Manager, after the course end date |

Attendance correction `PATCH /attendance/records/<id>/` accepts `{ status, reason }`. The reason is required for the manager and must be at least 5 characters. A teacher is still refused.

## Errors

- `400` business rule, such as a full course or a fourth installment
- `403` wrong role or another center
- `404` the object is outside the caller's queryset, including another center's id
- `409` duplicate enrollment, schedule clash, a second active contract, a second scholarship, or a reused idempotency key with a different payload

Cross-center attempts are written to the audit log with level `security`.
