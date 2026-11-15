# Dashboards and role navigation

Each role lands on `/` after login. The sidebar only lists routes that role may open. The API still rejects anything the menu hides.

| Group | Super Admin | Centre Manager | Finance | Teacher | Student |
| --- | --- | --- | --- | --- | --- |
| Overview | Dashboard | Dashboard | Dashboard | Dashboard | Dashboard |
| Organisation | Centres, people, contracts | People, students, teachers, contracts | Students, own contract | Own contract | — |
| Academic | Courses | Courses, classes, schedule, enrolment, attendance | — | Courses, classes, schedule, attendance | Available courses, my courses, schedule, attendance |
| Finance | Invoices, refunds, reports | Invoices, payments, installments, scholarships, refunds, reports | Same, and they record money | — | Own invoices, payments, installments, scholarships, refunds |
| System | Settings | Centre settings | — | — | — |

Dashboard content, all from live responses:

- Super admin: centre, student, teacher, and course counts, collected cash and bank, centre table, audit activity.
- Centre manager: students, teachers, courses, classes, outstanding balance, refunds, recent enrolments, audit activity.
- Finance manager: collected, outstanding, overdue installments, pending refunds, monthly chart.
- Teacher: assigned courses and classes, present and absent marks, today’s meetings, own contract.
- Student: enrolled courses, attendance, outstanding balance, own registrations.

Exchange rates, reconciliation, payroll, exams, and holidays are not in this product, so those widgets are not shown.
