/**
 * Invoices, receipts, installment plans, scholarships, and refunds.
 * Finance records money. Only the center manager can approve a refund.
 */
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Badge, Button, Field, Input, Modal, Select, StatCard, TextArea } from '../components/ui';
import { money, personName, todayISO, addDays } from '../utils/format';
import { createPaymentKey, paymentBody } from '../utils/paymentIntent';

function useSummary(centerId) {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  useEffect(() => {
    if (!['super_admin', 'center_manager', 'finance_manager'].includes(user?.role)) return undefined;
    if (user.role === 'super_admin' && !centerId) return undefined;
    const query = user.role === 'super_admin' ? `?center=${centerId}` : '';
    client.get(`/finance/summary/${query}`).then((response) => setSummary(unwrap(response))).catch(() => setSummary(null));
    return undefined;
  }, [user, centerId]);
  return summary;
}

export function FinancePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const centers = usePaged(user?.role === 'super_admin' ? '/centers/' : '');
  const [centerId, setCenterId] = useState('');
  const summary = useSummary(centerId);
  const list = usePaged(user?.role === 'super_admin' && centerId ? `/finance/invoices/?center=${centerId}` : '/finance/invoices/');
  const currency = summary?.currency || 'AFN';
  return (
    <div className="grid">
      <div className="page-head">
        <h2>{t('nav.finance')}</h2>
        {user?.role === 'super_admin' ? (
          <Field label={t('common.center')}>
            <Select value={centerId} onChange={(event) => setCenterId(event.target.value)}>
              <option value="">{t('common.choose')}</option>
              {centers.rows.map((center) => <option key={center.id} value={center.id}>{center.name}</option>)}
            </Select>
          </Field>
        ) : null}
      </div>
      {summary ? (
        <div className="grid stats">
          <StatCard label={t('common.expected')} value={money(summary.expected_revenue, currency)} />
          <StatCard label={t('common.collected')} value={money(summary.collected_payments, currency)} />
          <StatCard label={t('common.outstanding')} value={money(summary.outstanding_payments, currency)} />
          <StatCard label={t('common.refunds')} value={money(summary.refunds, currency)} />
        </div>
      ) : null}
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'number', label: t('common.invoice'), render: (row) => row.invoice_number },
          { key: 'student', label: t('common.student'), render: (row) => user?.role === 'student' ? row.course_name : personName(row.student) },
          { key: 'course', label: t('common.course'), render: (row) => row.course_name },
          { key: 'net', label: t('common.net'), render: (row) => money(row.net_amount) },
          { key: 'paid', label: t('common.paid'), render: (row) => money(row.paid_amount) },
          { key: 'out', label: t('common.outstanding'), render: (row) => money(row.outstanding) },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
        ]}
      />
    </div>
  );
}

export function PaymentsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/finance/payments/');
  const invoices = usePaged('/finance/invoices/');
  const [open, setOpen] = useState(false);
  const [intentKey, setIntentKey] = useState('');
  const [receipt, setReceipt] = useState(null);
  const form = useForm({ defaultValues: { method: 'cash' } });
  const method = form.watch('method');
  const finance = user?.role === 'finance_manager';
  return (
    <div>
      <div className="page-head">
        <h2>{t('nav.payments')}</h2>
        {finance ? <Button onClick={() => { setIntentKey(createPaymentKey()); setReceipt(null); setOpen(true); }}>{t('pages.newPayment')}</Button> : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'date', label: t('common.date'), render: (row) => String(row.paid_at).slice(0, 16).replace('T', ' ') },
          { key: 'student', label: t('common.student'), render: (row) => personName(row.student) },
          { key: 'amount', label: t('common.amount'), render: (row) => money(row.amount) },
          { key: 'method', label: t('common.method'), render: (row) => t(`common.${row.method}`) },
          { key: 'reference', label: t('common.reference') },
          { key: 'receipt', label: t('common.receipt'), render: (row) => (
            <Button variant="ghost" onClick={async () => {
              try {
                const response = await client.get(`/finance/payments/${row.id}/receipt/`);
                const data = unwrap(response);
                toast(`${data.receipt_number}: ${data.statement}`, 'success');
              } catch (err) {
                toast(errorMessage(err), 'danger');
              }
            }}>{row.receipt_number || t('common.receipt')}</Button>
          ) },
        ]}
      />
      <Modal title={t('pages.newPayment')} open={open} onClose={() => setOpen(false)}>
        <p className="muted">{t('common.bankHint')}</p>
        {receipt ? <p>{receipt.receipt_number} · {receipt.replayed ? t('common.paymentReplay') : t('common.saved')}</p> : null}
        <form className="grid" onSubmit={form.handleSubmit(async (values) => {
          try {
            const response = await client.post('/finance/payments/', paymentBody(intentKey, values));
            const data = unwrap(response);
            setReceipt(data);
            toast(data.replayed ? t('common.paymentReplay') : t('common.saved'), 'success');
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field label={t('common.invoice')}>
            <Select {...form.register('invoice', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {invoices.rows.map((invoice) => (
                <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {personName(invoice.student)} · {money(invoice.outstanding)}</option>
              ))}
            </Select>
          </Field>
          <Field label={t('common.amount')}><Input type="number" step="0.01" {...form.register('amount', { required: true })} /></Field>
          <Field label={t('common.method')}>
            <Select {...form.register('method')}>
              <option value="cash">{t('common.cash')}</option>
              <option value="bank">{t('common.bank')}</option>
            </Select>
          </Field>
          {method === 'bank' ? <Field label={t('common.reference')}><Input {...form.register('reference')} /></Field> : null}
          <Button type="submit">{t('common.save')}</Button>
        </form>
      </Modal>
    </div>
  );
}

export function InstallmentsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/finance/installments/');
  const invoices = usePaged('/finance/invoices/');
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(2);
  const finance = user?.role === 'finance_manager';
  return (
    <div>
      <div className="page-head">
        <h2>{t('nav.installments')}</h2>
        {finance ? <Button onClick={() => setOpen(true)}>{t('common.plan')}</Button> : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'number', label: t('common.number') },
          { key: 'due', label: t('common.due'), render: (row) => row.due_date },
          { key: 'amount', label: t('common.amount'), render: (row) => money(row.amount) },
          { key: 'paid', label: t('common.paid'), render: (row) => money(row.paid_amount) },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
        ]}
      />
      <Modal title={t('common.plan')} open={open} onClose={() => setOpen(false)}>
        <p className="muted">{t('common.installmentHint')}</p>
        <form className="grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const installments = [];
          for (let index = 0; index < count; index += 1) {
            installments.push({ due_date: data.get(`due-${index}`), amount: data.get(`amount-${index}`) });
          }
          try {
            await client.post('/finance/installments/plan/', { invoice: Number(data.get('invoice')), installments });
            toast(t('common.saved'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.invoice')}>
            <Select name="invoice" required>
              <option value="">{t('common.choose')}</option>
              {invoices.rows.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {money(invoice.net_amount)}</option>)}
            </Select>
          </Field>
          <Field label={t('common.number')}>
            <Select value={count} onChange={(event) => setCount(Number(event.target.value))}>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </Select>
          </Field>
          {Array.from({ length: count }).map((_, index) => (
            <div className="form-grid" key={index}>
              <Field label={`${t('common.due')} ${index + 1}`}><Input type="date" name={`due-${index}`} defaultValue={addDays(todayISO(), 30 * (index + 1))} required /></Field>
              <Field label={t('common.amount')}><Input type="number" step="0.01" name={`amount-${index}`} required /></Field>
            </div>
          ))}
          <Button type="submit">{t('common.save')}</Button>
        </form>
      </Modal>
    </div>
  );
}

export function ScholarshipsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/finance/scholarships/');
  const enrollments = usePaged('/enrollments/?status=active');
  const [open, setOpen] = useState(false);
  const [applyOpen, setApplyOpen] = useState(false);
  const finance = user?.role === 'finance_manager';
  return (
    <div>
      <div className="page-head">
        <h2>{t('nav.scholarships')}</h2>
        {finance ? (
          <div className="row-actions">
            <Button variant="ghost" onClick={() => setApplyOpen(true)}>{t('pages.applyScholarship')}</Button>
            <Button onClick={() => setOpen(true)}>{t('pages.newScholarship')}</Button>
          </div>
        ) : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'name', label: t('common.name') },
          { key: 'type', label: t('common.type'), render: (row) => t(`common.${row.scholarship_type}`) },
          { key: 'value', label: t('common.value') },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.is_active ? 'active' : 'inactive'} label={row.is_active ? t('common.active') : t('common.inactive')} /> },
        ]}
      />
      <Modal title={t('pages.newScholarship')} open={open} onClose={() => setOpen(false)}>
        <form className="grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          try {
            await client.post('/finance/scholarships/', {
              name: data.get('name'),
              scholarship_type: data.get('type'),
              value: data.get('value'),
              description: data.get('description'),
            });
            toast(t('common.created'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.name')}><Input name="name" required /></Field>
          <Field label={t('common.type')}>
            <Select name="type"><option value="percentage">{t('common.percentage')}</option><option value="fixed">{t('common.fixed')}</option></Select>
          </Field>
          <Field label={t('common.value')}><Input name="value" type="number" step="0.01" required /></Field>
          <Field label={t('common.description')}><TextArea name="description" /></Field>
          <Button type="submit">{t('common.create')}</Button>
        </form>
      </Modal>
      <Modal title={t('pages.applyScholarship')} open={applyOpen} onClose={() => setApplyOpen(false)}>
        <form className="grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          try {
            await client.post('/finance/scholarships/apply/', {
              scholarship: Number(data.get('scholarship')),
              enrollment: Number(data.get('enrollment')),
            });
            toast(t('common.saved'), 'success');
            setApplyOpen(false);
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('nav.scholarships')}>
            <Select name="scholarship" required>
              {list.rows.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </Select>
          </Field>
          <Field label={t('common.student')}>
            <Select name="enrollment" required>
              {enrollments.rows.map((item) => <option key={item.id} value={item.id}>{personName(item.student)} · {item.course?.name}</option>)}
            </Select>
          </Field>
          <Button type="submit">{t('common.apply')}</Button>
        </form>
      </Modal>
    </div>
  );
}

export function RefundsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/finance/refunds/');
  const invoices = usePaged('/finance/invoices/');
  const [open, setOpen] = useState(false);
  const canRequest = user?.role === 'finance_manager' || user?.role === 'student';
  const manager = user?.role === 'center_manager';
  return (
    <div>
      <div className="page-head">
        <div>
          <h2>{t('nav.refunds')}</h2>
          <p className="muted">{t('common.refundMeaning')}</p>
        </div>
        {canRequest ? <Button onClick={() => setOpen(true)}>{t('common.requestRefund')}</Button> : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'invoice', label: t('common.invoice'), render: (row) => row.invoice_number },
          { key: 'student', label: t('common.student'), render: (row) => personName(row.student) },
          { key: 'amount', label: t('common.amount'), render: (row) => money(row.amount) },
          { key: 'reason', label: t('common.reason') },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
          { key: 'actions', label: t('common.actions'), render: (row) => manager && row.status === 'pending' ? (
            <div className="row-actions">
              <Button onClick={() => review(row.id, 'approve')}>{t('common.approve')}</Button>
              <Button variant="danger" onClick={() => review(row.id, 'reject')}>{t('common.reject')}</Button>
            </div>
          ) : null },
        ]}
      />
      <Modal title={t('common.requestRefund')} open={open} onClose={() => setOpen(false)}>
        <form className="grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          try {
            await client.post('/finance/refunds/', {
              invoice: Number(data.get('invoice')),
              amount: data.get('amount'),
              reason: data.get('reason'),
            });
            toast(t('common.created'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.invoice')}>
            <Select name="invoice" required>
              {invoices.rows.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {money(invoice.paid_amount)}</option>)}
            </Select>
          </Field>
          <Field label={t('common.amount')}><Input name="amount" type="number" step="0.01" required /></Field>
          <Field label={t('common.reason')}><TextArea name="reason" required minLength={5} /></Field>
          <Button type="submit">{t('common.submit')}</Button>
        </form>
      </Modal>
    </div>
  );

  function review(id, action) {
    const note = window.prompt(t('common.decisionNote')) || '';
    client.post(`/finance/refunds/${id}/${action}/`, { decision_note: note }).then(() => {
      toast(t('common.saved'), 'success');
      list.reload();
    }).catch((err) => toast(errorMessage(err), 'danger'));
  }
}
