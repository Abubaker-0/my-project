import { Navigate, Route, Routes } from "react-router-dom";

import { AttendancePage } from "../features/attendance/AttendancePage";
import { AuditPage } from "../features/audit/AuditPage";
import { ForgotPasswordPage } from "../features/auth/ForgotPasswordPage";
import { LoginPage } from "../features/auth/LoginPage";
import { ResetPasswordPage } from "../features/auth/ResetPasswordPage";
import { FeesPage } from "../features/billing/FeesPage";
import { InvoiceDetailPage } from "../features/billing/InvoiceDetailPage";
import { InvoicesPage } from "../features/billing/InvoicesPage";
import { BatchDetailPage } from "../features/batches/BatchDetailPage";
import { BatchesPage } from "../features/batches/BatchesPage";
import { CourseDetailPage } from "../features/courses/CourseDetailPage";
import { CoursesPage } from "../features/courses/CoursesPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { InquiryDetailPage } from "../features/inquiries/InquiryDetailPage";
import { InquiriesPage } from "../features/inquiries/InquiriesPage";
import { AcademicYearsPage } from "../features/organization/AcademicYearsPage";
import { BranchDetailPage } from "../features/organization/BranchDetailPage";
import { BranchesPage } from "../features/organization/BranchesPage";
import { RoomDetailPage } from "../features/organization/RoomDetailPage";
import { RoomsPage } from "../features/organization/RoomsPage";
import { YearDetailPage } from "../features/organization/YearDetailPage";
import { RolesPage } from "../features/roles/RolesPage";
import { StudentDetailPage } from "../features/students/StudentDetailPage";
import { StudentsPage } from "../features/students/StudentsPage";
import { TimetablePage } from "../features/timetable/TimetablePage";
import { ForbiddenPage } from "../features/system/ForbiddenPage";
import { NotFoundPage } from "../features/system/NotFoundPage";
import { UsersPage } from "../features/users/UsersPage";
import { AppLayout } from "./AppLayout";
import { RequireAuth } from "./RequireAuth";
import { RequirePermission } from "./RequirePermission";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route
            path="inquiries"
            element={
              <RequirePermission permission="inquiries:read">
                <InquiriesPage />
              </RequirePermission>
            }
          />
          <Route
            path="inquiries/:inquiryId"
            element={
              <RequirePermission permission="inquiries:read">
                <InquiryDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="students"
            element={
              <RequirePermission permission="students:read">
                <StudentsPage />
              </RequirePermission>
            }
          />
          <Route
            path="students/:studentId"
            element={
              <RequirePermission permission="students:read">
                <StudentDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="courses"
            element={
              <RequirePermission permission="courses:read">
                <CoursesPage />
              </RequirePermission>
            }
          />
          <Route
            path="courses/:courseId"
            element={
              <RequirePermission permission="courses:read">
                <CourseDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="batches"
            element={
              <RequirePermission permission="batches:read">
                <BatchesPage />
              </RequirePermission>
            }
          />
          <Route
            path="timetable"
            element={
              <RequirePermission permission="timetable:read">
                <TimetablePage />
              </RequirePermission>
            }
          />
          <Route
            path="attendance"
            element={
              <RequirePermission permission="attendance:read">
                <AttendancePage />
              </RequirePermission>
            }
          />
          <Route
            path="fees"
            element={
              <RequirePermission permission="fees:read">
                <FeesPage />
              </RequirePermission>
            }
          />
          <Route
            path="invoices"
            element={
              <RequirePermission permission="invoices:read">
                <InvoicesPage />
              </RequirePermission>
            }
          />
          <Route
            path="invoices/:invoiceId"
            element={
              <RequirePermission permission="invoices:read">
                <InvoiceDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="batches/:batchId"
            element={
              <RequirePermission permission="batches:read">
                <BatchDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="academic-years"
            element={
              <RequirePermission permission="academic_years:read">
                <AcademicYearsPage />
              </RequirePermission>
            }
          />
          <Route
            path="academic-years/:yearId"
            element={
              <RequirePermission permission="academic_years:read">
                <YearDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="rooms"
            element={
              <RequirePermission permission="rooms:read">
                <RoomsPage />
              </RequirePermission>
            }
          />
          <Route
            path="rooms/:roomId"
            element={
              <RequirePermission permission="rooms:read">
                <RoomDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="branches"
            element={
              <RequirePermission permission="branches:read">
                <BranchesPage />
              </RequirePermission>
            }
          />
          <Route
            path="branches/:branchId"
            element={
              <RequirePermission permission="branches:read">
                <BranchDetailPage />
              </RequirePermission>
            }
          />
          <Route
            path="users"
            element={
              <RequirePermission permission="users:read">
                <UsersPage />
              </RequirePermission>
            }
          />
          <Route
            path="roles"
            element={
              <RequirePermission permission="roles:read">
                <RolesPage />
              </RequirePermission>
            }
          />
          <Route
            path="audit"
            element={
              <RequirePermission permission="audit:read">
                <AuditPage />
              </RequirePermission>
            }
          />
          <Route path="forbidden" element={<ForbiddenPage />} />
        </Route>
      </Route>
      <Route path="/home" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
