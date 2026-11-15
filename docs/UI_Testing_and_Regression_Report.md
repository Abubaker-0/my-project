# UI testing and regression report

## Baseline

Before this visual pass, `apps.common.tests.test_business_rules` had 16 passing tests. Those tests were run again after the interface work. The backend files were not changed for the redesign.

## Automated

| Suite | Result |
| --- | --- |
| `python manage.py test apps.common.tests.test_business_rules` | 16 passed |
| `npm test` (`theme.test.js`, `login.test.jsx`, `navigation.test.js`) | 5 passed |

The login test checks that the welcome form has no role selector, the lamp control is present, and sign-in stays enabled. The navigation test checks that teachers do not see finance, students do not see user administration, and the super admin does not see class creation in the menu.

## Browser

The running Vite app was checked at desktop and at 390px:

- Login, light and dark, including the lamp cord.
- Super admin, centre manager, finance manager, teacher, and student dashboards against live seed data.
- Mobile drawer open and closed.
- Dari right-to-left login.

Screenshots of the implemented screens are in `docs/screenshots/`.

A later pass fixed three visible defects: the monthly chart bars now use the computed primary color, the sidebar subtitle stays on one line, invoice statuses `partial` and `unpaid` are translated, empty stat icons are omitted, and `/profile` is named in the breadcrumb.

## Left unchanged

JWT, centre isolation, enrolment capacity, attendance correction, cash and bank payments, the three-installment cap, scholarships, and refund approval. No exchange-rate or reconciliation feature was added.
