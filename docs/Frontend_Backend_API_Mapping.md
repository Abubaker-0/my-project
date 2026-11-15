# Frontend and backend mapping

The client reads the JSON envelope `{ success, message, data }`. Lists use `data.results`. Auth is `Authorization: Bearer`.

| Screen | Method and path | Notes |
| --- | --- | --- |
| Login | POST `/auth/login/` | Username or email. Returns tokens and the user. No role field is sent. |
| Refresh / logout | POST `/auth/refresh/`, POST `/auth/logout/` | Refresh rotates. Logout blacklists. |
| Forgot password | POST `/auth/forgot-password/`, POST `/auth/reset-password/` | Debug builds return a token for local use. |
| Profile | GET/PATCH `/profile/`, POST `/profile/photo/`, GET `/profile/photo/<id>/` | Photo bytes require the token. |
| Dashboard | GET `/reports/dashboard/` | Role-scoped KPIs, monthly revenue, schedule, contract, centre rows. |
| Activity | GET `/reports/audit-logs/` | Super admin and the centre manager only. |
| Centres | `/centers/`, assign-manager, settings, statistics, logo | Super admin writes. |
| People and contracts | `/users/`, `/contracts/` | Creation rules stay in the services. |
| Courses and classes | `/courses/`, `/classes/`, `/classes/classrooms/` | Manager creates. Students see their sections. |
| Enrolment | `/enrollments/`, self-enroll, manual, approve, reject | Capacity and centre checks stay on the server. |
| Attendance | `/attendance/`, roster, mark, records patch | Teacher submits. Manager corrects. |
| Finance | `/finance/invoices/`, payments, installments, scholarships, refunds, summary | Cash and bank only. Manager approves refunds. |
| Reports | `/reports/financial/` | Finance drafts, manager sends. |

Request field names were not renamed. A 403 or 404 from another centre is shown as an error or an empty state, not as another centre’s data.
