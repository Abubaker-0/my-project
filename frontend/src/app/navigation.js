export const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/inquiries", label: "Inquiries", permission: "inquiries:read" },
  { to: "/students", label: "Students", permission: "students:read" },
  { to: "/courses", label: "Courses", permission: "courses:read" },
  { to: "/batches", label: "Batches", permission: "batches:read" },
  { to: "/academic-years", label: "Academic years", permission: "academic_years:read" },
  { to: "/rooms", label: "Rooms", permission: "rooms:read" },
  { to: "/branches", label: "Branches", permission: "branches:read" },
  { to: "/users", label: "Users", permission: "users:read" },
  { to: "/roles", label: "Roles", permission: "roles:read" },
  { to: "/audit", label: "Audit log", permission: "audit:read" },
];
