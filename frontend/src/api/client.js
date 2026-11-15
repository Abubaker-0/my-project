import axios from "axios";

import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";
import { attachRefreshInterceptor } from "./attachRefresh";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

const refreshClient = axios.create({
  baseURL: api.defaults.baseURL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export function refreshAccessToken() {
  return refreshClient.post("/auth/refresh", {}).then((response) => response.data.access_token);
}

attachRefreshInterceptor(api, {
  refresh: refreshAccessToken,
  setToken: (token) => useAuthStore.getState().setAccessToken(token),
  onFailure: () => {
    useAuthStore.getState().clear();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign("/login");
    }
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const branchId = useUiStore.getState().branchId;
  if (branchId) {
    config.headers["X-Branch-Id"] = String(branchId);
  }
  return config;
});
