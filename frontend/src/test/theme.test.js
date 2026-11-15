import { describe, expect, it } from 'vitest';
import { resolveTheme } from '../theme';

describe('theme preference', () => {
  it('keeps an explicit light or dark choice', () => {
    expect(resolveTheme('light')).toBe('light');
    expect(resolveTheme('dark')).toBe('dark');
  });

  it('treats an unknown value as light', () => {
    expect(resolveTheme('evergreen')).toBe('light');
  });
});
