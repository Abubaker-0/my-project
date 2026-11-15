/**
 * Sidebar entries. A link is shown only when the signed-in role is listed.
 * The API still rejects a request that slips past this menu.
 */
/** Groups keep the menu readable. Items still come from NAV and the user's role. */
export const NAV_GROUPS = [
  { id: 'overview', label: 'group.overview', keys: ['dashboard'] },
  { id: 'organisation', label: 'group.organisation', keys: ['centers', 'users', 'students', 'teachers', 'contracts'] },
  { id: 'academic', label: 'group.academic', keys: ['courses', 'availableCourses', 'myCourses', 'classes', 'schedule', 'enrollments', 'attendance'] },
  { id: 'finance', label: 'group.finance', keys: ['finance', 'payments', 'installments', 'scholarships', 'refunds', 'reports'] },
  { id: 'system', label: 'group.system', keys: ['settings', 'governance'] },
];

export const NAV = [
  { to: '/', key: 'dashboard', icon: 'LayoutDashboard', roles: ['super_admin', 'center_manager', 'finance_manager', 'teacher', 'student'] },
  { to: '/centers', key: 'centers', icon: 'Building2', roles: ['super_admin'] },
  { to: '/users', key: 'users', icon: 'Users', roles: ['super_admin', 'center_manager'] },
  { to: '/students', key: 'students', icon: 'GraduationCap', roles: ['center_manager', 'finance_manager'] },
  { to: '/teachers', key: 'teachers', icon: 'Presentation', roles: ['center_manager'] },
  { to: '/contracts', key: 'contracts', icon: 'FileSignature', roles: ['super_admin', 'center_manager', 'finance_manager', 'teacher'] },
  { to: '/courses', key: 'courses', icon: 'BookOpen', roles: ['super_admin', 'center_manager', 'teacher'] },
  { to: '/available-courses', key: 'availableCourses', icon: 'Library', roles: ['student'] },
  { to: '/my-courses', key: 'myCourses', icon: 'BookMarked', roles: ['student'] },
  { to: '/classes', key: 'classes', icon: 'School', roles: ['center_manager', 'teacher'] },
  { to: '/schedule', key: 'schedule', icon: 'CalendarDays', roles: ['center_manager', 'teacher', 'student'] },
  { to: '/enrollments', key: 'enrollments', icon: 'UserPlus', roles: ['center_manager'] },
  { to: '/attendance', key: 'attendance', icon: 'ClipboardCheck', roles: ['center_manager', 'teacher', 'student'] },
  { to: '/finance', key: 'finance', icon: 'Wallet', roles: ['super_admin', 'center_manager', 'finance_manager', 'student'] },
  { to: '/payments', key: 'payments', icon: 'Banknote', roles: ['center_manager', 'finance_manager', 'student'] },
  { to: '/installments', key: 'installments', icon: 'CalendarClock', roles: ['center_manager', 'finance_manager', 'student'] },
  { to: '/scholarships', key: 'scholarships', icon: 'Award', roles: ['center_manager', 'finance_manager', 'student'] },
  { to: '/refunds', key: 'refunds', icon: 'Undo2', roles: ['super_admin', 'center_manager', 'finance_manager', 'student'] },
  { to: '/reports', key: 'reports', icon: 'BarChart3', roles: ['super_admin', 'center_manager', 'finance_manager'] },
  { to: '/settings', key: 'settings', icon: 'Settings', roles: ['super_admin', 'center_manager'] },
  { to: '/governance', key: 'governance', icon: 'ShieldCheck', roles: ['super_admin'] },
];

/** Longest matching route wins, so /courses never captures /courses/1's siblings. */
export function pageKey(pathname) {
  if (!pathname || pathname === '/') return 'dashboard';
  if (pathname === '/profile' || pathname.startsWith('/profile/')) return 'profile';
  if (pathname === '/forbidden' || pathname.startsWith('/forbidden/')) return 'forbidden';
  const match = NAV
    .filter((item) => item.to !== '/')
    .sort((a, b) => b.to.length - a.to.length)
    .find((item) => pathname === item.to || pathname.startsWith(`${item.to}/`));
  return match?.key || 'dashboard';
}
