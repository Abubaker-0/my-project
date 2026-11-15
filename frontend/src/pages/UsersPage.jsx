/**
 * People directory. Super admin creates center managers only. A center manager
 * creates finance staff, teachers, and students inside their own center.
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { usePaged } from '../hooks/usePaged';
import { ContractFields, emptyContract } from '../components/ContractFields';
import { DataTable } from '../components/DataTable';
import { Avatar, Badge, Button, ConfirmDialog, Field, FilterDropdown, Input, Modal, SearchInput, Select } from '../components/ui';
import { personName } from '../utils/format';

export function UsersPage({ lockedRole, titleKey }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/users/', lockedRole ? { role: lockedRole } : {});
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const canCreate = user?.role === 'super_admin' || user?.role === 'center_manager';
  const roles = user?.role === 'super_admin' ? ['center_manager'] : ['finance_manager', 'teacher', 'student'];
  const form = useForm({
    defaultValues: {
      role: roles[0], gender: 'male', contract: emptyContract,
    },
  });
  const role = form.watch('role');
  const needsContract = role === 'teacher' || role === 'finance_manager';

  return (
    <div>
      <div className="page-head">
        <h2>{t(titleKey || 'pages.people')}</h2>
        {canCreate && !lockedRole ? <Button onClick={() => setOpen(true)}>{t('pages.newPerson')}</Button> : null}
        {canCreate && lockedRole && lockedRole !== 'center_manager' ? <Button onClick={() => { form.setValue('role', lockedRole); setOpen(true); }}>{t('pages.newPerson')}</Button> : null}
      </div>
      <div className="toolbar">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder={t('common.search')} />
        {!lockedRole ? (
          <FilterDropdown
            label={t('common.role')}
            value={list.filters.role || ''}
            onChange={(value) => list.setFilters({ ...list.filters, role: value })}
            options={[{ value: '', label: t('common.all') }, ...['super_admin', 'center_manager', 'finance_manager', 'teacher', 'student'].map((item) => ({ value: item, label: t(`roles.${item}`) }))]}
          />
        ) : null}
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
          { key: 'name', label: t('common.name'), sort: 'first_name', render: (row) => (
            <div className="person"><Avatar name={personName(row)} photo={row.photo_url} /><div><strong>{personName(row)}</strong><small className="muted">{row.username}</small></div></div>
          ) },
          { key: 'role', label: t('common.role'), render: (row) => t(`roles.${row.role}`) },
          { key: 'phone', label: t('common.phone') },
          { key: 'center', label: t('common.center'), render: (row) => row.center?.name || '—' },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.is_active ? 'active' : 'inactive'} label={row.is_active ? t('common.active') : t('common.inactive')} /> },
          { key: 'actions', label: t('common.actions'), render: (row) => (
            <div className="row-actions">
              {user?.role === 'center_manager' && row.role !== 'center_manager' ? <Button variant="ghost" onClick={() => setEditing(row)}>{t('common.edit')}</Button> : null}
              {user?.role === 'super_admin' && row.role === 'center_manager' ? <Button variant="ghost" onClick={() => setEditing(row)}>{t('common.edit')}</Button> : null}
              <Button variant="ghost" onClick={() => setConfirm(row)}>{row.is_active ? t('common.deactivate') : t('common.activate')}</Button>
            </div>
          ) },
        ]}
      />
      <Modal title={t('pages.newPerson')} open={open} onClose={() => setOpen(false)}>
        <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
          const payload = {
            username: values.username,
            email: values.email,
            password: values.password,
            first_name: values.first_name,
            last_name: values.last_name,
            phone: values.phone,
            gender: values.gender,
            role: values.role,
            address: values.address || '',
          };
          if (needsContract) payload.contract = values.contract;
          try {
            await client.post('/users/', payload);
            toast(t('common.created'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field label={t('common.firstName')}><Input {...form.register('first_name', { required: true })} /></Field>
          <Field label={t('common.lastName')}><Input {...form.register('last_name', { required: true })} /></Field>
          <Field label={t('common.username')}><Input {...form.register('username', { required: true })} /></Field>
          <Field label={t('common.email')}><Input {...form.register('email', { required: true })} /></Field>
          <Field label={t('common.phone')}><Input {...form.register('phone', { required: true })} /></Field>
          <Field label={t('common.password')}><Input type="password" {...form.register('password', { required: true })} /></Field>
          <Field label={t('common.gender')}>
            <Select {...form.register('gender')}>
              <option value="male">{t('common.male')}</option>
              <option value="female">{t('common.female')}</option>
            </Select>
          </Field>
          <Field label={t('common.role')}>
            <Select {...form.register('role')}>
              {roles.map((item) => <option key={item} value={item}>{t(`roles.${item}`)}</option>)}
            </Select>
          </Field>
          {needsContract ? <ContractFields register={form.register} setValue={form.setValue} watch={form.watch} /> : null}
          <p className="muted wide">{t('common.passwordHint')}</p>
          <div className="row-actions wide"><Button type="submit">{t('common.create')}</Button></div>
        </form>
      </Modal>
      <Modal title={t('pages.editPerson')} open={Boolean(editing)} onClose={() => setEditing(null)}>
        {editing ? (
          <EditPerson person={editing} onDone={() => { setEditing(null); list.reload(); }} />
        ) : null}
      </Modal>
      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.is_active ? t('common.deactivate') : t('common.activate')}
        message={t('common.confirmDeactivate')}
        confirmLabel={t('common.confirm')}
        cancelLabel={t('common.cancel')}
        onClose={() => setConfirm(null)}
        onConfirm={async () => {
          try {
            await client.post(`/users/${confirm.id}/${confirm.is_active ? 'deactivate' : 'activate'}/`);
            toast(t('common.saved'), 'success');
            setConfirm(null);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}
      />
    </div>
  );
}

function EditPerson({ person, onDone }) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { user } = useAuth();
  const form = useForm({ defaultValues: person });
  return (
    <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
      try {
        await client.patch(`/users/${person.id}/`, {
          first_name: values.first_name,
          last_name: values.last_name,
          phone: values.phone,
          gender: values.gender,
          email: values.email,
          address: values.address || '',
          bio: values.bio || '',
        });
        if (user?.role === 'center_manager' && values.role && values.role !== person.role && person.role !== 'center_manager') {
          await client.post(`/users/${person.id}/role/`, { role: values.role });
        }
        toast(t('common.saved'), 'success');
        onDone();
      } catch (err) {
        toast(errorMessage(err), 'danger');
      }
    })}>
      <Field label={t('common.firstName')}><Input {...form.register('first_name')} /></Field>
      <Field label={t('common.lastName')}><Input {...form.register('last_name')} /></Field>
      <Field label={t('common.email')}><Input {...form.register('email')} /></Field>
      <Field label={t('common.phone')}><Input {...form.register('phone')} /></Field>
      <Field label={t('common.gender')}>
        <Select {...form.register('gender')}>
          <option value="male">{t('common.male')}</option>
          <option value="female">{t('common.female')}</option>
        </Select>
      </Field>
      {user?.role === 'center_manager' && person.role !== 'center_manager' ? (
        <Field label={t('common.role')}>
          <Select {...form.register('role')}>
            {['finance_manager', 'teacher', 'student'].map((item) => <option key={item} value={item}>{t(`roles.${item}`)}</option>)}
          </Select>
        </Field>
      ) : null}
      <Field className="wide" label={t('common.address')}><Input {...form.register('address')} /></Field>
      <div className="row-actions wide"><Button type="submit">{t('common.save')}</Button></div>
    </form>
  );
}
