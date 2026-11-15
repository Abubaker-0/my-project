/**
 * Signed-in user and token storage.
 *
 * Login stores the JWT pair. On reload, /auth/me rebuilds the profile.
 * Role checks in the UI are a convenience; the API still enforces them.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import client, { clearTokens, errorMessage, storeTokens, unwrap } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const loadMe = useCallback(async () => {
    const response = await client.get('/auth/me/');
    const profile = unwrap(response);
    setUser(profile);
    return profile;
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('ctcms-access');
    if (!token) {
      setReady(true);
      return;
    }
    loadMe().catch(() => {
      clearTokens();
      setUser(null);
    }).finally(() => setReady(true));
  }, [loadMe]);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener('ctcms-logout', onLogout);
    return () => window.removeEventListener('ctcms-logout', onLogout);
  }, []);

  const login = useCallback(async (username, password) => {
    const response = await client.post('/auth/login/', { username, password });
    const data = unwrap(response);
    storeTokens(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('ctcms-refresh');
    try {
      if (refresh) await client.post('/auth/logout/', { refresh });
    } catch {
      // A dead refresh token should still leave the browser signed out.
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(() => ({
    user,
    ready,
    login,
    logout,
    refreshUser: loadMe,
    setUser,
    errorMessage,
  }), [user, ready, login, logout, loadMe]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
