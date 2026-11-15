/**
 * Route map. ProtectedRoute requires a session. RoleGuard matches the menu.
 * Center-bound pages also pass through CenterGuard.
 */
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { RoleGuard } from './components/RoleGuard';
import { CenterGuard } from './components/CenterGuard';
import { LoginPage } from './pages/LoginPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { CentersPage } from './pages/CentersPage';
import { CenterDetailPage } from './pages/CenterDetailPage';
import { UsersPage } from './pages/UsersPage';
import { ContractsPage } from './pages/ContractsPage';
import { CoursesPage } from './pages/CoursesPage';
import { CourseDetailPage } from './pages/CourseDetailPage';
import { ClassesPage } from './pages/ClassesPage';
import { SchedulePage } from './pages/SchedulePage';
import { EnrollmentsPage } from './pages/EnrollmentsPage';
import { AvailableCoursesPage, MyCoursesPage } from './pages/CatalogPages';
import { AttendancePage } from './pages/AttendancePage';
import { FinancePage, InstallmentsPage, PaymentsPage, RefundsPage, ScholarshipsPage } from './pages/FinancePages';
import { ReportsPage } from './pages/ReportsPage';
import { ProfilePage } from './pages/ProfilePage';
import { CenterSettingsRoute, SettingsPage } from './pages/SettingsPage';
import { ForbiddenPage } from './pages/ForbiddenPage';
import { GovernancePage } from './pages/GovernancePage';

function guard(roles, node, center = false) {
  const body = center ? <CenterGuard>{node}</CenterGuard> : node;
  return (
    <RoleGuard roles={roles}>
      {body}
    </RoleGuard>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="centers" element={guard(['super_admin'], <CentersPage />)} />
        <Route path="centers/:id" element={guard(['super_admin', 'center_manager'], <CenterDetailPage />)} />
        <Route path="centers/:id/settings" element={guard(['super_admin', 'center_manager', 'finance_manager'], <CenterSettingsRoute />)} />
        <Route path="users" element={guard(['super_admin', 'center_manager'], <UsersPage />)} />
        <Route path="students" element={guard(['center_manager', 'finance_manager'], <UsersPage lockedRole="student" titleKey="nav.students" />, true)} />
        <Route path="teachers" element={guard(['center_manager'], <UsersPage lockedRole="teacher" titleKey="nav.teachers" />, true)} />
        <Route path="contracts" element={guard(['super_admin', 'center_manager', 'finance_manager', 'teacher'], <ContractsPage />)} />
        <Route path="courses" element={guard(['super_admin', 'center_manager', 'teacher'], <CoursesPage />)} />
        <Route path="courses/:id" element={guard(['super_admin', 'center_manager', 'teacher', 'student', 'finance_manager'], <CourseDetailPage />)} />
        <Route path="available-courses" element={guard(['student'], <AvailableCoursesPage />, true)} />
        <Route path="my-courses" element={guard(['student'], <MyCoursesPage />, true)} />
        <Route path="classes" element={guard(['center_manager', 'teacher'], <ClassesPage />, true)} />
        <Route path="schedule" element={guard(['center_manager', 'teacher', 'student'], <SchedulePage />, true)} />
        <Route path="enrollments" element={guard(['center_manager'], <EnrollmentsPage />, true)} />
        <Route path="attendance" element={guard(['center_manager', 'teacher', 'student'], <AttendancePage />, true)} />
        <Route path="finance" element={guard(['super_admin', 'center_manager', 'finance_manager', 'student'], <FinancePage />)} />
        <Route path="payments" element={guard(['center_manager', 'finance_manager', 'student'], <PaymentsPage />)} />
        <Route path="installments" element={guard(['center_manager', 'finance_manager', 'student'], <InstallmentsPage />)} />
        <Route path="scholarships" element={guard(['center_manager', 'finance_manager', 'student'], <ScholarshipsPage />)} />
        <Route path="refunds" element={guard(['super_admin', 'center_manager', 'finance_manager', 'student'], <RefundsPage />)} />
        <Route path="reports" element={guard(['super_admin', 'center_manager', 'finance_manager'], <ReportsPage />)} />
        <Route path="settings" element={guard(['super_admin', 'center_manager'], <SettingsPage />)} />
        <Route path="governance" element={guard(['super_admin'], <GovernancePage />)} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="forbidden" element={<ForbiddenPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
