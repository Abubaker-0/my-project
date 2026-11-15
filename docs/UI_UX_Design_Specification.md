# UI and UX specification

The interface follows the PohanaHub reference: a split academic login, a dark sidebar, parchment pages, and ivory cards. Evergreen Academic is the default. The React app keeps the existing routes, JWT login, and centre rules.

## Login

One screen serves all five roles. There is no role picker. The API returns the role and the app opens the matching dashboard.

The left panel carries the brand, the headline “A brighter way to manage learning.”, and a cord lamp. The lamp is decorative. Pulling the cord turns on a warm glow. The form stays usable when the lamp is off and when the user prefers reduced motion.

The right panel has username or email, password with a show/hide control, a remember-username checkbox, a forgot-password link, and the sign-in button. Remember-me stores only the username in local storage. The password and the session still come from the API. Local demo accounts sit behind a disclosure so the form matches the reference and testers can still fill a role.

## Workspace

Signed-in pages share one shell:

- A dark sidebar with grouped links for the current role, a collapse control on desktop, and a drawer on narrow screens.
- A header with the breadcrumb, language, theme, activity, and profile menu.
- A content area with a serif page title, KPI cards, a monthly collection chart, recent activity or today’s classes, and a table of real records.

Activity is the audit log for the super admin and the centre manager. Other roles see today’s schedule or an empty state. Counts and money come from `/reports/dashboard/` and related list endpoints. Nothing on the dashboard is a sample figure.

## Pages

Every existing module uses the same tokens: centres, people, contracts, courses, classes, schedule, enrolment, attendance, invoices, payments, installments, scholarships, refunds, reports, settings, and profile. Buttons still call the existing API actions.

## Language and motion

English is left to right. Dari is right to left, including the sidebar and the lamp. Theme and palette are applied before React renders. Color changes are short. `prefers-reduced-motion` removes animation.
