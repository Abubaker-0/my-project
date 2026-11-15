/**
 * Sidebar entries. A link is shown only when the signed-in role is listed.
 * The API still rejects a request that slips past this menu.
 */
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
];
