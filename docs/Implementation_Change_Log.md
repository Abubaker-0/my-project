# Implementation change log

Visual modernization of the existing React app. The Django API, MySQL schema, and business rules were not replaced.

## Interface

- Replaced the indigo paper theme with Evergreen Academic tokens, plus optional Sapphire and Royal Indigo.
- Added light, dark, and system theme without a startup flash.
- Rebuilt the login into the split layout with a cord lamp, password visibility, remember-username, and a collapsed demo-account list.
- Rebuilt the sidebar, header, breadcrumbs, profile menu, and activity list.
- Restyled shared cards, tables, forms, badges, dialogs, and charts so existing module pages inherit the system.
- Reworked the five role dashboards to the new layout while binding them to live responses.
- Chart bars read the computed `--primary` color so they stay visible in both themes.
- Invoice statuses `partial` and `unpaid`, plus `completed` and `withdrawn`, have English and Dari labels.
- The breadcrumb uses the longest matching route, and profile is labeled as Profile.

## Left unchanged

- JWT login, refresh, logout, and centre checks.
- Course, class, enrolment, attendance, payment, installment, scholarship, refund, and contract rules.
- No exchange-rate, reconciliation, payroll, exam, or holiday module was added.

## Tests

- Backend `apps.common.tests.test_business_rules`: 16 passed. No backend behavior was changed in this pass.
- Frontend `npm test`: theme resolution, unified login, and role menus.
