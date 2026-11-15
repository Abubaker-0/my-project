/**
 * Workflow helpers and the permission screen. API enforcement stays in Django tests.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '../context/ToastContext';
import { applyLanguage } from '../i18n';
import { GovernancePage } from '../pages/GovernancePage';
import { createPaymentKey, paymentBody } from '../utils/paymentIntent';

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/permissions/matrix/') {
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
            code: 'finance.collect',
            protected: true,
            scope: 'own center',
            conditions: 'Active contract.',
            cells: { finance_manager: { allowed: true, source: 'protected', configurable: false } },
          }],
        } });
      }
      if (url === '/permissions/history/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: { issues: [] } });
    }),
    post: vi.fn(() => Promise.resolve({ data: { closes: ['POST /api/reports/financial/'], effect: 'The next request uses this result.' } })),
  },
  unwrap: (response) => response.data,
  errorMessage: () => 'failed',
}));

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
    expect(screen.getByText(/cannot remove|not stored as a grant/i)).toBeInTheDocument();
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
