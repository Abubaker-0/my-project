/**
 * Persists theme and palette. The resolved theme is what CSS reads,
 * so "system" follows the OS without a flash after the first paint.
 */
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { PALETTE_KEY, THEME_KEY, applyAppearance, resolveTheme } from '../theme';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || 'light');
  const [palette, setPalette] = useState(() => localStorage.getItem(PALETTE_KEY) || 'evergreen');

  useEffect(() => {
    applyAppearance(theme, palette);
    localStorage.setItem(THEME_KEY, theme);
    localStorage.setItem(PALETTE_KEY, palette);
    if (theme !== 'system') return undefined;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => applyAppearance('system', palette);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, [theme, palette]);

  const value = useMemo(() => ({
    theme,
    palette,
    resolved: resolveTheme(theme),
    setTheme,
    setPalette,
    toggleTheme: () => setTheme(resolveTheme(theme) === 'dark' ? 'light' : 'dark'),
  }), [theme, palette]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
