/**
 * Light and dark theme. The choice is stored in localStorage and applied
 * as data-theme on the document element before paint when possible.
 */
import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const KEY = 'ctcms-theme';
const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem(KEY) || 'light');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const value = useMemo(() => ({
    theme,
    toggleTheme: () => setTheme((current) => (current === 'light' ? 'dark' : 'light')),
  }), [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
