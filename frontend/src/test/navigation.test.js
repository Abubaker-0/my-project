/**
 * Menu visibility is a convenience. Each role still only sees its own links.
 */
import { describe, expect, it } from 'vitest';
import { NAV, pageKey } from '../nav';

function keysFor(role) {
  return NAV.filter((item) => item.roles.includes(role)).map((item) => item.key);
}

describe('role navigation', () => {
  it('gives every role a dashboard and keeps centre writes with the manager', () => {
    for (const role of ['super_admin', 'center_manager', 'finance_manager', 'teacher', 'student']) {
      expect(keysFor(role)).toContain('dashboard');
    }
    expect(keysFor('super_admin')).toContain('centers');
    expect(keysFor('super_admin')).not.toContain('classes');
    expect(keysFor('teacher')).not.toContain('finance');
    expect(keysFor('student')).toContain('availableCourses');
    expect(keysFor('student')).not.toContain('users');
    expect(keysFor('finance_manager')).toContain('payments');
    expect(keysFor('finance_manager')).not.toContain('courses');
  });

  it('names profile and nested routes from the longest match', () => {
    expect(pageKey('/')).toBe('dashboard');
    expect(pageKey('/profile')).toBe('profile');
    expect(pageKey('/courses/12')).toBe('courses');
    expect(pageKey('/available-courses')).toBe('availableCourses');
    expect(pageKey('/centers/3/settings')).toBe('centers');
  });
});
