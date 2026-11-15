/**
 * Center directory. Only the super admin can open this page and create centers.
 * Day-to-day course work stays with the center manager.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import client, { errorMessage } from '../api/client';
import { useToast } from '../context/ToastContext';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Badge, Button, Field, FilterDropdown, Input, Modal, SearchInput } from '../components/ui';
import { personName } from '../utils/format';

export function CentersPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const list = usePaged('/centers/');
  const [open, setOpen] = useState(false);
  const schema = z.object({
    name: z.string().min(1, t('validation.required')),
    code: z.string().min(2, t('validation.required')),
    city: z.string().optional(),
    phone: z.string().optional(),
    email: z.string().email(t('validation.email')).or(z.literal('')).optional(),
    address: z.string().optional(),
    description: z.string().optional(),
  });
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ resolver: zodResolver(schema) });

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>{t('pages.centers')}</h2>
        </div>
        <Button onClick={() => setOpen(true)}>{t('pages.newCenter')}</Button>
      </div>
      <div className="toolbar">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder={t('common.search')} />
        <FilterDropdown
          label={t('common.status')}
          value={list.filters.is_active || ''}
          onChange={(value) => list.setFilters({ ...list.filters, is_active: value })}
          options={[{ value: '', label: t('common.all') }, { value: 'true', label: t('common.active') }, { value: 'false', label: t('common.inactive') }]}
        />
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        onSort={list.setOrdering}
        columns={[
          { key: 'name', label: t('common.name'), sort: 'name', render: (row) => <Link to={`/centers/${row.id}`}>{row.name}</Link> },
          { key: 'code', label: t('common.code'), sort: 'code' },
          { key: 'city', label: t('common.city') },
          { key: 'manager', label: t('common.manager'), render: (row) => personName(row.manager) || t('common.none') },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.is_active ? 'active' : 'inactive'} label={row.is_active ? t('common.active') : t('common.inactive')} /> },
        ]}
      />
      <Modal title={t('pages.newCenter')} open={open} onClose={() => setOpen(false)}>
        <form className="form-grid" onSubmit={handleSubmit(async (values) => {
          try {
            await client.post('/centers/', values);
            toast(t('common.created'), 'success');
            reset();
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field label={t('common.name')} error={errors.name?.message}><Input {...register('name')} /></Field>
          <Field label={t('common.code')} error={errors.code?.message}><Input {...register('code')} /></Field>
          <Field label={t('common.city')}><Input {...register('city')} /></Field>
          <Field label={t('common.phone')}><Input {...register('phone')} /></Field>
          <Field className="wide" label={t('common.email')} error={errors.email?.message}><Input {...register('email')} /></Field>
          <Field className="wide" label={t('common.address')}><Input {...register('address')} /></Field>
          <Field className="wide" label={t('common.description')}><Input {...register('description')} /></Field>
          <div className="row-actions wide">
            <Button type="submit" disabled={isSubmitting}>{t('common.create')}</Button>
            <Button variant="ghost" onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
