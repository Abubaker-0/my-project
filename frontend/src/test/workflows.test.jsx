/**
 * Workflow screens. These tests check what the interface sends.
 * Authorization and money rules stay in the Django suite.
 */
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { ToastProvider } from '../context/ToastContext';
import { applyLanguage } from '../i18n';
import { AttendancePage } from '../pages/AttendancePage';
import { MyCoursesPage } from '../pages/CatalogPages';
import { EnrollmentsPage } from '../pages/EnrollmentsPage';
import { PaymentsPage, RefundsPage } from '../pages/FinancePages';
import { GovernancePage } from '../pages/GovernancePage';
import { ReportsPage } from '../pages/ReportsPage';
import { SettingsPage } from '../pages/SettingsPage';
import { Topbar } from '../components/Topbar';
import { ToastViewport } from '../components/Toast';
import { createPaymentKey, paymentBody } from '../utils/paymentIntent';
import '../i18n';

const session = vi.hoisted(() => ({
  user: null,
  posts: [],
  paymentKey: '',
  denyPrepare: false,
  reportStatus: 'submitted_to_manager',
}));

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn((url) => {
      const path = String(url).split('?')[0];
      if (path === '/auth/me/') return Promise.resolve({ data: session.user });
      if (path === '/permissions/matrix/') {
        return Promise.resolve({ data: {
          roles: ['finance_manager'],
          lockout: 'Protected governance access stays with the super admin role and is not stored as a grant.',
          rows: [{
            code: 'reports.prepare',
            protected: false,
            scope: 'own center',
            conditions: 'Create, submit, and revise all use this code.',
            cells: { finance_manager: { allowed: true, source: 'default', configurable: true } },
          }, {
            code: 'exports.invoices',
            protected: false,
            scope: 'own center',
            conditions: 'A denial closes the invoice export.',
            cells: { finance_manager: { allowed: true, source: 'default', configurable: true } },
          }, {
            code: 'finance.collect',
            protected: true,
            scope: 'own center',
            conditions: 'Active contract.',
            cells: { finance_manager: { allowed: true, source: 'protected', configurable: false } },
          }],
        } });
      }
      if (path === '/permissions/history/') {
        return Promise.resolve({ data: [{ version: 4, code: 'exports.invoices', role: 'finance_manager', reason: 'Term close' }] });
      }
      if (path === '/reports/integrity/') return Promise.resolve({ data: { issues: [] } });
      if (path === '/settings/global/') {
        return Promise.resolve({ data: {
          organization_name: 'Course Tuition Center MIS', support_email: '', support_phone: '',
          allow_self_enrollment: true, require_enrollment_approval: false, allow_waitlist: true,
          allow_student_refund_requests: true, allow_finance_refund_requests: true,
          max_installments: 3, default_allow_self_enrollment: true,
        } });
      }
      if (path === '/centers/1/settings/') {
        return Promise.resolve({ data: {
          allow_self_enrollment: true, require_enrollment_approval: false, allow_waitlist: true,
          allow_student_refund_requests: true, allow_finance_refund_requests: true, max_installments: 2,
        } });
      }
      if (path === '/settings/effective/') {
        return Promise.resolve({ data: { rules: {
          self_enrollment: { effective: true, source: 'global and center', effect: 'Later enrollments only.' },
        } } });
      }
      if (path === '/finance/payments/9/receipt/') {
        return Promise.resolve({ data: { receipt_number: 'RCP-1', statement: 'Recorded cash of 10.00 AFN.' } });
      }
      if (path === '/finance/payments/') {
        return Promise.resolve({ data: { count: 1, results: [{
          id: 9, paid_at: '2026-11-01T10:00:00Z', student: { first_name: 'Ali', last_name: 'Ahmadi' },
          amount: '10.00', method: 'cash', reference: '', receipt_number: 'RCP-1',
        }] } });
      }
      if (path === '/finance/invoices/') {
        return Promise.resolve({ data: { count: 1, results: [{
          id: 4, invoice_number: 'INV-1', outstanding: '100.00', paid_amount: '50.00',
          student: { first_name: 'Ali', last_name: 'Ahmadi' },
        }] } });
      }
      if (path === '/finance/refunds/') {
        return Promise.resolve({ data: { count: 1, results: [{
          id: 3, invoice_number: 'INV-1', student: { first_name: 'Ali', last_name: 'Ahmadi' },
          amount: '20.00', reason: 'Left the course', status: 'pending',
        }] } });
      }
      if (path === '/enrollments/waitlist/') {
        return Promise.resolve({ data: [{ id: 2, status: 'waiting', student: 'Omar Karimi', course: 'Math' }] });
      }
      if (path === '/enrollments/withdrawals/') {
        return Promise.resolve({ data: [{ id: 5, status: 'pending', student: 'Maryam Rahimi', reason: 'Moving city' }] });
      }
      if (path === '/enrollments/') {
        return Promise.resolve({ data: { count: 1, results: [{
          id: 8, status: 'active', source: 'self', created_at: '2026-09-01T08:00:00Z',
          student: { first_name: 'Ali', last_name: 'Ahmadi' },
          course: { id: 1, name: 'Math' }, course_class: { name: 'Morning' },
        }] } });
      }
      if (path === '/classes/') return Promise.resolve({ data: { results: [{ id: 1, course_name: 'Math', name: 'Morning' }] } });
      if (path === '/attendance/') return Promise.resolve({ data: { count: 0, results: [] } });
      if (path === '/attendance/roster/') {
        return Promise.resolve({ data: {
          submitted: true,
          students: [{ student: { id: 7, first_name: 'Ali', last_name: 'Ahmadi' }, status: 'present', record_id: 11 }],
        } });
      }
      if (path === '/reports/financial/') {
        return Promise.resolve({ data: { count: 1, results: [{
          id: 6, title: 'September', center_name: 'Kabul', period_start: '2026-09-01', period_end: '2026-09-30',
          prepared_by_name: 'Finance Kabul', status: session.reportStatus,
          snapshot: { expected_revenue: '100', collected_payments: '40', outstanding_payments: '60', scholarships: '0', refunds: '0', currency: 'AFN' },
        }] } });
      }
      if (path === '/notifications/') {
        return Promise.resolve({ data: [{ id: 1, title: 'Your contract ends in 30 days', created_at: '2026-11-01T08:00:00Z' }] });
      }
      if (path === '/reports/audit-logs/') return Promise.resolve({ data: { results: [] } });
      if (path === '/finance/summary/') return Promise.resolve({ data: { currency: 'AFN', expected_revenue: '0', collected_payments: '0', outstanding_payments: '0', refunds: '0' } });
      return Promise.resolve({ data: { results: [], count: 0 } });
    }),
    post: vi.fn((url, body) => {
      session.posts.push({ url, body });
      if (url === '/permissions/preview/') {
        const closes = body.code === 'exports.invoices'
          ? ['GET /api/reports/export/invoices/']
          : ['POST /api/reports/financial/'];
        return Promise.resolve({ data: {
          code: body.code, current_allowed: true, proposed_allowed: body.allowed,
          effect: 'The next request uses this result.', closes,
        } });
      }
      if (url === '/finance/payments/') {
        const replayed = Boolean(session.paymentKey) && body.idempotency_key === session.paymentKey;
        session.paymentKey = body.idempotency_key;
        return Promise.resolve({ data: { id: 9, receipt_number: 'RCP-1', replayed } });
      }
      if (String(url).endsWith('/revise/') && session.denyPrepare) {
        return Promise.reject({ response: { data: { message: 'Report preparation is restricted for this center.' } } });
      }
      return Promise.resolve({ data: {} });
    }),
    patch: vi.fn((url, body) => {
      session.posts.push({ url, body });
      return Promise.resolve({ data: body });
    }),
  },
  unwrap: (response) => response.data,
  errorMessage: (error) => error?.response?.data?.message || 'failed',
  clearTokens: () => {
    localStorage.removeItem('ctcms-access');
    localStorage.removeItem('ctcms-refresh');
  },
  storeTokens: () => {},
}));

afterEach(() => {
  cleanup();
  localStorage.clear();
  session.posts = [];
  session.paymentKey = '';
  session.denyPrepare = false;
  session.reportStatus = 'submitted_to_manager';
  session.user = null;
  vi.unstubAllGlobals();
});

function signedIn(user, node) {
  session.user = user;
  localStorage.setItem('ctcms-access', 'live-token');
  return render(
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <ToastViewport />
          <MemoryRouter>{node}</MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>,
  );
}

const finance = { id: 3, role: 'finance_manager', first_name: 'Finance', last_name: 'Kabul', center: { id: 1 } };
const manager = { id: 2, role: 'center_manager', first_name: 'Manager', last_name: 'Kabul', center: { id: 1 } };
const teacher = { id: 4, role: 'teacher', first_name: 'Zahra', last_name: 'Nazari', center: { id: 1 } };
const student = { id: 5, role: 'student', first_name: 'Ali', last_name: 'Ahmadi', center: { id: 1 } };

describe('payment intent', () => {
  it('reuses one key for retries and changes it for a new payment', () => {
    const first = createPaymentKey();
    const retry = paymentBody(first, { invoice: '4', amount: '10.00', method: 'cash', reference: '' });
    const again = paymentBody(first, { invoice: '4', amount: '10.00', method: 'cash', reference: '' });
    expect(again.idempotency_key).toBe(retry.idempotency_key);
    expect(createPaymentKey()).not.toBe(first);
  });
});

describe('permission administration', () => {
  it('shows protected duties and configurable report preparation', async () => {
    render(<ToastProvider><GovernancePage /></ToastProvider>);
    expect(await screen.findByText('reports.prepare')).toBeInTheDocument();
    expect(screen.getByText('finance.collect')).toBeInTheDocument();
    expect(screen.getAllByText('protected').length).toBeGreaterThan(0);
    expect(screen.getByText(/not stored as a grant/i)).toBeInTheDocument();
  });

  it('previews an export denial and restores a recorded version', async () => {
    render(<ToastProvider><GovernancePage /></ToastProvider>);
    fireEvent.change(await screen.findByLabelText(/reason/i), { target: { value: 'Close export for this term' } });
    const previews = screen.getAllByRole('button', { name: 'Preview' });
    fireEvent.click(previews[1]);
    expect(await screen.findByText((_, node) => node?.tagName === 'P' && node.textContent.includes('GET /api/reports/export/invoices/'))).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: 'Restore' })[0]);
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/permissions/restore/' && item.body.version === 4 && item.body.reason === 'Close export for this term')).toBe(true);
    });
  });
});

describe('effective policy', () => {
  it('shows the resolved rule and keeps the currency label AFN', async () => {
    signedIn({ ...manager, role: 'super_admin' }, <SettingsPage />);
    expect(await screen.findByDisplayValue('AFN')).toBeDisabled();
    expect(screen.getByLabelText(/default for a new center/i)).toBeInTheDocument();
    cleanup();
    signedIn(manager, <SettingsPage />);
    expect(await screen.findByText('self_enrollment')).toBeInTheDocument();
    expect(screen.getByText(/Later enrollments only/)).toBeInTheDocument();
    expect(screen.getByText(/global and center/)).toBeInTheDocument();
  });
});

describe('enrollment and withdrawal', () => {
  it('promotes a waiter and decides a withdrawal', async () => {
    signedIn(manager, <EnrollmentsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Offer the seat' }));
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/enrollments/promote-waitlist/' && item.body.id === 2)).toBe(true);
      expect(session.posts.some((item) => item.url === '/enrollments/decide-withdrawal/' && item.body.approve === true)).toBe(true);
    });
  });

  it('sends a student withdrawal reason', async () => {
    vi.stubGlobal('prompt', () => 'I need to leave this course');
    signedIn(student, <MyCoursesPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Request withdrawal' }));
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/enrollments/8/withdraw/' && item.body.reason === 'I need to leave this course')).toBe(true);
    });
  });
});

describe('attendance correction', () => {
  it('sends the manager reason with the corrected mark', async () => {
    signedIn(manager, <AttendancePage />);
    fireEvent.change(await screen.findByLabelText('Class'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'View' }));
    fireEvent.change(await screen.findByLabelText('Reason'), { target: { value: 'The register had the wrong mark' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }));
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/attendance/records/11/' && item.body.reason === 'The register had the wrong mark')).toBe(true);
    });
  });

  it('lets a teacher request a correction without editing the mark', async () => {
    vi.stubGlobal('prompt', () => 'Please change this to absent');
    signedIn(teacher, <AttendancePage />);
    fireEvent.change(await screen.findByLabelText('Class'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'View' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Request correction' }));
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/attendance/correction-requests/' && item.body.record_id === 11)).toBe(true);
    });
    expect(session.posts.some((item) => String(item.url).includes('/attendance/records/'))).toBe(false);
  });
});

describe('payments and refunds', () => {
  it('reuses the payment key on a second submit and opens the receipt', async () => {
    signedIn(finance, <PaymentsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Record payment' }));
    fireEvent.change(await screen.findByLabelText('Invoice'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: '10.00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await screen.findByText(/RCP-1/);
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText((_, node) => node?.tagName === 'P' && node.textContent.includes('already recorded'))).toBeInTheDocument();
    const payments = session.posts.filter((item) => item.url === '/finance/payments/');
    expect(payments).toHaveLength(2);
    expect(payments[0].body.idempotency_key).toBeTruthy();
    expect(payments[1].body.idempotency_key).toBe(payments[0].body.idempotency_key);
    fireEvent.click(screen.getByRole('button', { name: 'RCP-1' }));
    expect(await screen.findByText(/Recorded cash of 10.00 AFN/)).toBeInTheDocument();
  });

  it('sends a refund approval from the manager', async () => {
    vi.stubGlobal('prompt', () => 'Approved against the collected cash');
    signedIn(manager, <RefundsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }));
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/finance/refunds/3/approve/' && item.body.decision_note === 'Approved against the collected cash')).toBe(true);
    });
  });
});

describe('reports', () => {
  it('returns a submitted report with a note', async () => {
    vi.stubGlobal('prompt', () => 'The collected total needs another look');
    signedIn(manager, <ReportsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Return' }));
    await waitFor(() => {
      expect(session.posts.some((item) => item.url === '/reports/financial/6/return/' && item.body.note === 'The collected total needs another look')).toBe(true);
    });
  });

  it('shows a revoked prepare permission on the existing session', async () => {
    session.reportStatus = 'returned';
    session.denyPrepare = true;
    signedIn(finance, <ReportsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'New revision' }));
    expect(await screen.findByText('Report preparation is restricted for this center.')).toBeInTheDocument();
  });
});

describe('notifications and session', () => {
  it('shows only the notices returned for the signed-in person', async () => {
    signedIn(teacher, <Topbar title="Attendance" />);
    expect(await screen.findByText('Zahra Nazari')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Activity' }));
    expect(await screen.findByText('Your contract ends in 30 days')).toBeInTheDocument();
    expect(screen.queryByText('Someone else was paid')).not.toBeInTheDocument();
  });

  it('clears the signed-in person when the session ends', async () => {
    signedIn(teacher, <Topbar title="Attendance" />);
    expect(await screen.findByText('Zahra Nazari')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Zahra Nazari/ }));
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }));
    await waitFor(() => expect(screen.queryByText('Zahra Nazari')).not.toBeInTheDocument());
    window.dispatchEvent(new Event('ctcms-logout'));
    expect(localStorage.getItem('ctcms-access')).toBeNull();
  });
});

describe('direction', () => {
  it('flips the document between LTR and RTL', () => {
    applyLanguage('fa');
    expect(document.documentElement.dir).toBe('rtl');
    applyLanguage('en');
    expect(document.documentElement.dir).toBe('ltr');
  });
});
