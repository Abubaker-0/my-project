import { api } from "./client";

function clean(params) {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== undefined && value !== null && value !== "",
    ),
  );
}

export function fetchHealth() {
  return api.get("/health").then((response) => response.data);
}

export function listUsers(params) {
  return api.get("/users", { params: clean(params) }).then((response) => response.data);
}

export function createUser(payload) {
  return api.post("/users", payload).then((response) => response.data);
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`);
}

export function listRoles(params) {
  return api.get("/roles", { params: clean(params) }).then((response) => response.data);
}

export function listPermissions() {
  return api.get("/permissions").then((response) => response.data);
}

export function updateRolePermissions(roleId, permissionIds) {
  return api
    .put(`/roles/${roleId}/permissions`, { permission_ids: permissionIds })
    .then((response) => response.data);
}

export function listBranches(params = {}) {
  return api
    .get("/branches", { params: clean({ page_size: 100, ...params }) })
    .then((response) => response.data);
}

export function getBranch(id) {
  return api.get(`/branches/${id}`).then((response) => response.data);
}

export function listAuditLogs(params) {
  return api.get("/audit-logs", { params: clean(params) }).then((response) => response.data);
}

export function createBranch(payload) {
  return api.post("/branches", payload).then((response) => response.data);
}

export function updateBranch(id, payload) {
  return api.patch(`/branches/${id}`, payload).then((response) => response.data);
}

export function listAcademicYears(params) {
  return api.get("/academic-years", { params: clean(params) }).then((response) => response.data);
}

export function getAcademicYear(id) {
  return api.get(`/academic-years/${id}`).then((response) => response.data);
}

export function createAcademicYear(payload) {
  return api.post("/academic-years", payload).then((response) => response.data);
}

export function addTerm(yearId, payload) {
  return api.post(`/academic-years/${yearId}/terms`, payload).then((response) => response.data);
}

export function listRooms(params) {
  return api.get("/rooms", { params: clean(params) }).then((response) => response.data);
}

export function createRoom(payload) {
  return api.post("/rooms", payload).then((response) => response.data);
}

export function getRoom(id) {
  return api.get(`/rooms/${id}`).then((response) => response.data);
}

export function updateRoom(id, payload) {
  return api.patch(`/rooms/${id}`, payload).then((response) => response.data);
}

export function listSubjects(params) {
  return api.get("/subjects", { params: clean(params) }).then((response) => response.data);
}

export function createSubject(payload) {
  return api.post("/subjects", payload).then((response) => response.data);
}

export function listCourses(params) {
  return api.get("/courses", { params: clean(params) }).then((response) => response.data);
}

export function getCourse(id) {
  return api.get(`/courses/${id}`).then((response) => response.data);
}

export function createCourse(payload) {
  return api.post("/courses", payload).then((response) => response.data);
}

export function updateCourse(id, payload) {
  return api.patch(`/courses/${id}`, payload).then((response) => response.data);
}

export function listBatches(params) {
  return api.get("/batches", { params: clean(params) }).then((response) => response.data);
}

export function getBatch(id) {
  return api.get(`/batches/${id}`).then((response) => response.data);
}

export function createBatch(payload) {
  return api.post("/batches", payload).then((response) => response.data);
}

export function updateBatch(id, payload) {
  return api.patch(`/batches/${id}`, payload).then((response) => response.data);
}

export function assignTeacher(batchId, payload) {
  return api.post(`/batches/${batchId}/teachers`, payload).then((response) => response.data);
}

export function listStudents(params) {
  return api.get("/students", { params: clean(params) }).then((response) => response.data);
}

export function getStudent(id) {
  return api.get(`/students/${id}`).then((response) => response.data);
}

export function createStudent(payload) {
  return api.post("/students", payload).then((response) => response.data);
}

export function updateStudent(id, payload) {
  return api.patch(`/students/${id}`, payload).then((response) => response.data);
}

export function addGuardian(studentId, payload) {
  return api.post(`/students/${studentId}/guardians`, payload).then((response) => response.data);
}

export function uploadDocument(studentId, file, docType) {
  const body = new FormData();
  body.append("doc_type", docType);
  body.append("file", file);
  return api.post(`/students/${studentId}/documents`, body).then((response) => response.data);
}

export async function downloadDocument(studentId, documentId, fileName) {
  const response = await api.get(`/students/${studentId}/documents/${documentId}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export function listInquiries(params) {
  return api.get("/inquiries", { params: clean(params) }).then((response) => response.data);
}

export function getInquiry(id) {
  return api.get(`/inquiries/${id}`).then((response) => response.data);
}

export function createInquiry(payload) {
  return api.post("/inquiries", payload).then((response) => response.data);
}

export function updateInquiry(id, payload) {
  return api.patch(`/inquiries/${id}`, payload).then((response) => response.data);
}

export function addFollowup(id, payload) {
  return api.post(`/inquiries/${id}/followups`, payload).then((response) => response.data);
}

export function convertInquiry(id, payload) {
  return api.post(`/inquiries/${id}/convert`, payload).then((response) => response.data);
}

export function listEnrollments(params) {
  return api.get("/enrollments", { params: clean(params) }).then((response) => response.data);
}

export function createEnrollment(payload) {
  return api.post("/enrollments", payload).then((response) => response.data);
}

export function withdrawEnrollment(id, reason) {
  return api.post(`/enrollments/${id}/withdraw`, { reason }).then((response) => response.data);
}

export function listSessions(params) {
  return api
    .get("/timetable/sessions", { params: clean(params) })
    .then((response) => response.data);
}

export function createSession(payload) {
  return api.post("/timetable/sessions", payload).then((response) => response.data);
}

export function cancelSession(id) {
  return api.post(`/timetable/sessions/${id}/cancel`).then((response) => response.data);
}

export function getAttendance(batchId, attendedOn) {
  return api
    .get("/attendance/sheets", { params: { batch_id: batchId, attended_on: attendedOn } })
    .then((response) => response.data);
}

export function saveAttendance(payload) {
  return api.put("/attendance/sheets", payload).then((response) => response.data);
}

export function listFeePlans(params) {
  return api.get("/fee-plans", { params: clean(params) }).then((response) => response.data);
}

export function createFeePlan(payload) {
  return api.post("/fee-plans", payload).then((response) => response.data);
}

export function listInvoices(params) {
  return api.get("/invoices", { params: clean(params) }).then((response) => response.data);
}

export function getInvoice(id) {
  return api.get(`/invoices/${id}`).then((response) => response.data);
}

export function createInvoice(payload) {
  return api.post("/invoices", payload).then((response) => response.data);
}

export function cancelInvoice(id, reason) {
  return api.post(`/invoices/${id}/cancel`, { reason }).then((response) => response.data);
}

export function recordPayment(payload, idempotencyKey) {
  return api
    .post("/payments", payload, { headers: { "Idempotency-Key": idempotencyKey } })
    .then((response) => response.data);
}

export function voidPayment(id, reason) {
  return api.post(`/payments/${id}/void`, { reason }).then((response) => response.data);
}

export async function downloadReceipt(paymentId, receiptNo) {
  const response = await api.get(`/payments/${paymentId}/receipt`, { responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${receiptNo}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}

export function financeDashboard() {
  return api.get("/dashboard/finance").then((response) => response.data);
}

export function todayDashboard() {
  return api.get("/dashboard/today").then((response) => response.data);
}
