/**
 * Staff contracts. A new contract is allowed only after the previous one
 * has ended. The center manager ends a contract from this list.
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { usePaged } from '../hooks/usePaged';
import { ContractFields, emptyContract } from '../components/ContractFields';
import { DataTable } from '../components/DataTable';
import { Badge, Button, ConfirmDialog, Field, Modal, Select } from '../components/ui';
import { money, personName } from '../utils/format';

export function ContractsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/contracts/');
  const staff = useOptions(user?.role === 'center_manager' ? '/users/' : '');
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState(null);
  const form = useForm({ defaultValues: { contract: emptyContract } });
  const manager = user?.role === 'center_manager';
  return (
    <div>
      <div className="page-head">
        <h2>{t('nav.contracts')}</h2>
        {manager ? <Button onClick={() => setOpen(true)}>{t('common.create')}</Button> : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        onSort={list.setOrdering}
        columns={[
          { key: 'user', label: t('common.name'), render: (row) => row.user_name },
          { key: 'type', label: t('common.contractType'), render: (row) => t(`common.${row.contract_type}`) },
          { key: 'dates', label: t('common.period'), render: (row) => `${row.start_date} → ${row.end_date}` },
          { key: 'salary', label: t('common.salary'), render: (row) => `${money(row.salary_amount)} · ${t(`common.${row.salary_type}`)}` },
          { key: 'method', label: t('common.method'), render: (row) => t(`common.${row.payment_method}`) },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
          { key: 'actions', label: t('common.actions'), render: (row) => manager && row.status === 'active' ? (
            <Button variant="danger" onClick={() => setTarget(row)}>{t('status.terminated')}</Button>
          ) : null },
        ]}
      />
      <Modal title={t('common.contract')} open={open} onClose={() => setOpen(false)}>
        <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
          try {
            await client.post('/contracts/', { user: Number(values.user), ...values.contract });
            toast(t('common.created'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field className="wide" label={t('common.name')}>
            <Select {...form.register('user', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {staff.filter((person) => person.role === 'teacher' || person.role === 'finance_manager').map((person) => (
                <option key={person.id} value={person.id}>{personName(person)} · {t(`roles.${person.role}`)}</option>
              ))}
            </Select>
          </Field>
          <ContractFields register={form.register} setValue={form.setValue} watch={form.watch} />
          <div className="row-actions wide"><Button type="submit">{t('common.create')}</Button></div>
        </form>
      </Modal>
      <ConfirmDialog
        open={Boolean(target)}
        title={t('status.terminated')}
        message={t('common.confirmTerminate')}
        confirmLabel={t('common.confirm')}
        cancelLabel={t('common.cancel')}
        onClose={() => setTarget(null)}
        onConfirm={async () => {
          try {
            await client.post(`/contracts/${target.id}/terminate/`);
            toast(t('common.saved'), 'success');
            setTarget(null);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}
      />
    </div>
  );
}
