/**
 * One center: identity, the single active manager, statistics, and finance.
 * Assigning a manager uses only people who are free of an active contract.
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { ContractFields, emptyContract } from '../components/ContractFields';
import { Badge, Breadcrumbs, Button, Card, Field, Input, Modal, Select, StatCard } from '../components/ui';
import { money, personName } from '../utils/format';

export function CenterDetailPage() {
  const { id } = useParams();
  const { t } = useTranslation();
  const { toast } = useToast();
  const [center, setCenter] = useState(null);
  const [stats, setStats] = useState(null);
  const [open, setOpen] = useState(false);
  const managers = useOptions(open ? '/users/available-managers/' : '');
  const form = useForm({ defaultValues: { manager_id: '', replace: false, contract: emptyContract } });

  const load = () => {
    client.get(`/centers/${id}/`).then((response) => setCenter(unwrap(response))).catch((err) => toast(errorMessage(err), 'danger'));
    client.get(`/centers/${id}/statistics/`).then((response) => setStats(unwrap(response))).catch(() => setStats(null));
  };
  useEffect(load, [id]);

  if (!center) return null;
  const currency = stats?.finance?.currency || 'AFN';
  return (
    <div className="grid">
      <Breadcrumbs items={[{ to: '/centers', label: t('nav.centers') }, { label: center.name }]} />
      <div className="page-head">
        <div>
          <h2>{center.name}</h2>
          <p>{center.code} · {center.city}</p>
        </div>
        <div className="row-actions">
          <Badge value={center.is_active ? 'active' : 'inactive'} label={center.is_active ? t('common.active') : t('common.inactive')} />
          <Button variant="ghost" onClick={async () => {
            try {
              await client.post(`/centers/${id}/${center.is_active ? 'deactivate' : 'activate'}/`);
              toast(t('common.saved'), 'success');
              load();
            } catch (err) {
              toast(errorMessage(err), 'danger');
            }
          }}>{center.is_active ? t('common.deactivate') : t('common.activate')}</Button>
          <Button onClick={() => setOpen(true)}>{t('pages.assignManager')}</Button>
          <Link className="ghost" to={`/centers/${id}/settings`}>{t('nav.settings')}</Link>
        </div>
      </div>
      <div className="grid stats">
        <StatCard label={t('kpi.students')} value={stats?.students ?? '–'} />
        <StatCard label={t('kpi.teachers')} value={stats?.teachers ?? '–'} />
        <StatCard label={t('kpi.courses')} value={stats?.courses ?? '–'} />
        <StatCard label={t('common.collected')} value={money(stats?.finance?.collected_payments, currency)} />
      </div>
      <div className="grid split">
        <Card>
          <h3>{t('common.details')}</h3>
          <p>{center.description}</p>
          <p className="muted">{center.address}</p>
          <p>{center.phone} · {center.email}</p>
          <p>{t('common.manager')}: {personName(center.manager) || t('common.none')}</p>
        </Card>
        <Card>
          <h3>{t('common.finance')}</h3>
          <p>{t('common.expected')}: {money(stats?.finance?.expected_revenue, currency)}</p>
          <p>{t('common.outstanding')}: {money(stats?.finance?.outstanding_payments, currency)}</p>
          <p>{t('common.scholarships')}: {money(stats?.finance?.scholarships, currency)}</p>
          <p>{t('common.refunds')}: {money(stats?.finance?.refunds, currency)}</p>
        </Card>
      </div>
      <Modal title={t('pages.assignManager')} open={open} onClose={() => setOpen(false)}>
        <p className="muted">{t('common.assignHint')}</p>
        <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
          try {
            await client.post(`/centers/${id}/assign-manager/`, {
              manager_id: Number(values.manager_id),
              replace: Boolean(values.replace),
              contract: values.contract,
            });
            toast(t('common.saved'), 'success');
            setOpen(false);
            load();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field className="wide" label={t('common.manager')}>
            <Select {...form.register('manager_id')}>
              <option value="">{t('common.choose')}</option>
              {managers.map((manager) => <option key={manager.id} value={manager.id}>{personName(manager)}</option>)}
            </Select>
          </Field>
          <label className="check wide"><input type="checkbox" {...form.register('replace')} /> {t('common.replace')}</label>
          <ContractFields register={form.register} setValue={form.setValue} watch={form.watch} />
          <div className="row-actions wide">
            <Button type="submit">{t('common.save')}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
