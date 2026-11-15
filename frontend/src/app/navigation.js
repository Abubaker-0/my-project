export const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/users", label: "Users", permission: "users:read" },
  { to: "/roles", label: "Roles", permission: "roles:read" },
  { to: "/audit", label: "Audit log", permission: "audit:read" },
];
