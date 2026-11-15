/**
 * Appearance tokens applied before React paints.
 * Preference is light, dark, or the operating-system setting.
 * Palette is evergreen by default, with sapphire and indigo as alternates.
 */
export const THEME_KEY = 'ctcms-theme';
export const PALETTE_KEY = 'ctcms-palette';

export function resolveTheme(preference) {
  if (preference === 'dark') return 'dark';
  if (preference === 'system' && typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

export function applyAppearance(preference, palette) {
  const theme = resolveTheme(preference);
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.palette = palette || 'evergreen';
  document.documentElement.style.colorScheme = theme;
  return theme;
}
