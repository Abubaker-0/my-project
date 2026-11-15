import { api } from "./client";

export function login(payload) {
  return api.post("/auth/login", payload).then((response) => response.data);
}

export function logout() {
  return api.post("/auth/logout", {}).then((response) => response.data);
}

export function fetchMe(accessToken) {
  return api
    .get("/auth/me", { headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {} })
    .then((response) => response.data);
}

export function forgotPassword(email) {
  return api.post("/auth/forgot-password", { email }).then((response) => response.data);
}

export function resetPassword(payload) {
  return api.post("/auth/reset-password", payload).then((response) => response.data);
}

export function changePassword(payload) {
  return api.post("/auth/change-password", payload).then((response) => response.data);
}

export function fetchSessions() {
  return api.get("/auth/sessions").then((response) => response.data);
}
