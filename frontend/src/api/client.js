/**
 * Axios client for the tuition MIS API.
 *
 * Every JSON body is an envelope: { success, message, data }.
 * File downloads (profile photos, logos) skip the envelope because they are
 * binary responses. A 401 refreshes the JWT once, then signs the user out.
 */
import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

const ACCESS = 'ctcms-access';
const REFRESH = 'ctcms-refresh';

export function readTokens() {
  return {
    access: localStorage.getItem(ACCESS) || '',
    refresh: localStorage.getItem(REFRESH) || '',
  };
}

export function storeTokens(access, refresh) {
  if (access) localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

client.interceptors.request.use((config) => {
  const { access } = readTokens();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshPromise = null;

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;
    const isAuthCall = String(original.url || '').includes('/auth/login') || String(original.url || '').includes('/auth/refresh');
    if (status !== 401 || original._retry || isAuthCall) {
      return Promise.reject(error);
    }
    const { refresh } = readTokens();
    if (!refresh) {
      window.dispatchEvent(new Event('ctcms-logout'));
      return Promise.reject(error);
    }
    original._retry = true;
    try {
      refreshPromise = refreshPromise || axios.post(`${client.defaults.baseURL}/auth/refresh/`, { refresh });
      const response = await refreshPromise;
      refreshPromise = null;
      const body = response.data?.data || response.data;
      storeTokens(body.access, body.refresh);
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${body.access}`;
      return client(original);
    } catch (refreshError) {
      refreshPromise = null;
      clearTokens();
      window.dispatchEvent(new Event('ctcms-logout'));
      return Promise.reject(refreshError);
    }
  },
);

/** Pull the payload out of the standard success envelope. */
export function unwrap(response) {
  const body = response?.data;
  if (body && typeof body === 'object' && 'success' in body) return body.data;
  return body;
}

/** First human-readable error from an envelope or a network failure. */
export function errorMessage(error) {
  const body = error?.response?.data;
  if (!body) return error?.message || 'Request failed.';
  if (typeof body.message === 'string' && body.message && body.message !== 'Request failed.') return body.message;
  const errors = body.errors || body;
  if (typeof errors === 'string') return errors;
  if (Array.isArray(errors) && errors.length) return String(errors[0]);
  if (errors && typeof errors === 'object') {
    if (typeof errors.detail === 'string') return errors.detail;
    const first = Object.entries(errors)[0];
    if (first) {
      const value = Array.isArray(first[1]) ? first[1][0] : first[1];
      return `${first[0]}: ${value}`;
    }
  }
  return 'Request failed.';
}

export default client;
