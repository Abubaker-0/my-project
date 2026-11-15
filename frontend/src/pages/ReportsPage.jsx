/**
 * Official finance reports. Finance drafts and submits them.
 * The center manager sends a submitted report to the super admin.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import client, { errorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Badge, Button, Card, Field, Input, Modal, Select } from '../components/ui';
import { money, todayISO, addDays } from '../utils/format';

export function ReportsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/reports/financial/');
  const centers = useOptions(user?.role === 'super_admin' ? '/centers/' : '');
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const finance = user?.role === 'finance_manager';
  const manager = user?.role === 'center_manager';
  return (
    <div className="grid">
      <div className="page-head">
        <h2>{t('nav.reports')}</h2>
        {finance ? <Button onClick={() => setOpen(true)}>{t('pages.newReport')}</Button> : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'title', label: t('common.title'), render: (row) => <button type="button" className="ghost" onClick={() => setSelected(row)}>{row.title}</button> },
          { key: 'center', label: t('common.center'), render: (row) => row.center_name },
          { key: 'period', label: t('common.period'), render: (row) => `${row.period_start} → ${row.period_end}` },
          { key: 'by', label: t('common.prepared'), render: (row) => row.prepared_by_name },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
          { key: 'actions', label: t('common.actions'), render: (row) => (
            <div className="row-actions">
              {finance && row.status === 'draft' ? <Button onClick={() => act(row.id, 'submit')}>{t('common.submit')}</Button> : null}
              {finance && row.status === 'returned' ? <Button onClick={() => act(row.id, 'revise')}>{t('common.revise')}</Button> : null}
              {manager && row.status === 'submitted_to_manager' ? <Button onClick={() => act(row.id, 'send')}>{t('common.send')}</Button> : null}
              {manager && row.status === 'submitted_to_manager' ? <Button variant="ghost" onClick={() => {
                const note = window.prompt(t('common.returnReason'));
                if (!note) return;
                client.post(`/reports/financial/${row.id}/return/`, { note }).then(() => {
                  toast(t('common.saved'), 'success');
                  list.reload();
                }).catch((err) => toast(errorMessage(err), 'danger'));
              }}>{t('common.returnReport')}</Button> : null}
            </div>
          ) },
        ]}
      />
      {selected ? (
        <Card>
          <h3>{selected.title}</h3>
          <p>{money(selected.snapshot?.expected_revenue, selected.snapshot?.currency)} {t('common.expected')}</p>
          <p>{money(selected.snapshot?.collected_payments, selected.snapshot?.currency)} {t('common.collected')}</p>
          <p>{money(selected.snapshot?.outstanding_payments, selected.snapshot?.currency)} {t('common.outstanding')}</p>
          <p>{money(selected.snapshot?.scholarships, selected.snapshot?.currency)} {t('common.scholarships')}</p>
          <p>{money(selected.snapshot?.refunds, selected.snapshot?.currency)} {t('common.refunds')}</p>
        </Card>
      ) : null}
      <Modal title={t('pages.newReport')} open={open} onClose={() => setOpen(false)}>
        <form className="grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const payload = {
            title: data.get('title'),
            period_start: data.get('start'),
            period_end: data.get('end'),
          };
          if (user?.role === 'super_admin') payload.center = Number(data.get('center'));
          try {
            await client.post('/reports/financial/', payload);
            toast(t('common.created'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.title')}><Input name="title" required /></Field>
          {user?.role === 'super_admin' ? (
            <Field label={t('common.center')}>
              <Select name="center">{centers.map((center) => <option key={center.id} value={center.id}>{center.name}</option>)}</Select>
            </Field>
          ) : null}
          <Field label={t('common.from')}><Input type="date" name="start" defaultValue={addDays(todayISO(), -30)} required /></Field>
          <Field label={t('common.to')}><Input type="date" name="end" defaultValue={todayISO()} required /></Field>
          <Button type="submit">{t('common.create')}</Button>
        </form>
      </Modal>
    </div>
  );

  function act(id, action) {
    client.post(`/reports/financial/${id}/${action}/`).then(() => {
      toast(t('common.saved'), 'success');
      list.reload();
    }).catch((err) => toast(errorMessage(err), 'danger'));
  }
}
