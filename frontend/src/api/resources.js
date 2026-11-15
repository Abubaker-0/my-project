import { api } from "./client";

function clean(params) {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== undefined && value !== null && value !== "",
    ),
  );
}

export function fetchHealth() {
  return api.get("/health").then((response) => response.data);
}

export function listUsers(params) {
  return api.get("/users", { params: clean(params) }).then((response) => response.data);
}

export function createUser(payload) {
  return api.post("/users", payload).then((response) => response.data);
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`);
}

export function listRoles(params) {
  return api.get("/roles", { params: clean(params) }).then((response) => response.data);
}

export function listPermissions() {
  return api.get("/permissions").then((response) => response.data);
}

export function updateRolePermissions(roleId, permissionIds) {
  return api
    .put(`/roles/${roleId}/permissions`, { permission_ids: permissionIds })
    .then((response) => response.data);
}

export function listBranches(params = {}) {
  return api
    .get("/branches", { params: clean({ page_size: 100, ...params }) })
    .then((response) => response.data);
}

export function listAuditLogs(params) {
  return api.get("/audit-logs", { params: clean(params) }).then((response) => response.data);
}
