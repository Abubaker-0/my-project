/**
 * Organization settings for the super admin and center rules for the manager.
 * Installment caps cannot exceed 3, which the API also enforces.
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Button, Card, Field, Input, Select } from '../components/ui';

export function SettingsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  if (user?.role === 'super_admin') return <GlobalSettings />;
  return <CenterSettings centerId={user?.center?.id} />;
}

export function CenterSettingsRoute() {
  const { id } = useParams();
  return <CenterSettings centerId={id} />;
}

function GlobalSettings() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [values, setValues] = useState(null);
  useEffect(() => {
    client.get('/settings/global/').then((response) => setValues(unwrap(response))).catch((err) => toast(errorMessage(err), 'danger'));
  }, []);
  if (!values) return null;
  return (
    <Card>
      <h2>{t('pages.globalSettings')}</h2>
      <p className="muted">{t('common.policyProspective')}</p>
      <form className="form-grid" style={{ marginTop: 16 }} onSubmit={async (event) => {
        event.preventDefault();
        try {
          const response = await client.patch('/settings/global/', values);
          setValues(unwrap(response));
          toast(t('common.saved'), 'success');
        } catch (err) {
          toast(errorMessage(err), 'danger');
        }
      }}>
        <Field label={t('common.organization')}><Input value={values.organization_name || ''} onChange={(event) => setValues({ ...values, organization_name: event.target.value })} /></Field>
        <Field label={t('common.supportEmail')}><Input value={values.support_email || ''} onChange={(event) => setValues({ ...values, support_email: event.target.value })} /></Field>
        <Field label={t('common.supportPhone')}><Input value={values.support_phone || ''} onChange={(event) => setValues({ ...values, support_phone: event.target.value })} /></Field>
        <Field label={t('common.currency')}><Input value="AFN" disabled /></Field>
        <label className="check"><input type="checkbox" checked={values.allow_self_enrollment} onChange={(event) => setValues({ ...values, allow_self_enrollment: event.target.checked })} /> {t('common.selfEnrollCeiling')}</label>
        <label className="check"><input type="checkbox" checked={values.require_enrollment_approval} onChange={(event) => setValues({ ...values, require_enrollment_approval: event.target.checked })} /> {t('common.approvalRequired')}</label>
        <label className="check"><input type="checkbox" checked={values.allow_waitlist} onChange={(event) => setValues({ ...values, allow_waitlist: event.target.checked })} /> {t('common.waitlistCeiling')}</label>
        <label className="check"><input type="checkbox" checked={values.allow_student_refund_requests} onChange={(event) => setValues({ ...values, allow_student_refund_requests: event.target.checked })} /> {t('common.studentRefunds')}</label>
        <label className="check"><input type="checkbox" checked={values.allow_finance_refund_requests} onChange={(event) => setValues({ ...values, allow_finance_refund_requests: event.target.checked })} /> {t('common.financeRefunds')}</label>
        <Field label={t('common.maxInstallments')}>
          <Select value={values.max_installments} onChange={(event) => setValues({ ...values, max_installments: Number(event.target.value) })}>
            <option value={1}>1</option><option value={2}>2</option><option value={3}>3</option>
          </Select>
        </Field>
        <label className="check"><input type="checkbox" checked={values.default_allow_self_enrollment} onChange={(event) => setValues({ ...values, default_allow_self_enrollment: event.target.checked })} /> {t('common.selfEnrollDefault')}</label>
        <div className="row-actions wide"><Button type="submit">{t('common.save')}</Button></div>
      </form>
    </Card>
  );
}

function CenterSettings({ centerId }) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { user } = useAuth();
  const [values, setValues] = useState(null);
  useEffect(() => {
    if (!centerId) return;
    client.get(`/centers/${centerId}/settings/`).then((response) => setValues(unwrap(response))).catch((err) => toast(errorMessage(err), 'danger'));
  }, [centerId]);
  if (!values) return null;
  const editable = user?.role === 'center_manager';
  return (
    <Card>
      <h2>{t('pages.centerSettings')}</h2>
      <form className="grid" style={{ marginTop: 16 }} onSubmit={async (event) => {
        event.preventDefault();
        try {
          const response = await client.patch(`/centers/${centerId}/settings/`, values);
          setValues(unwrap(response));
          toast(t('common.saved'), 'success');
        } catch (err) {
          toast(errorMessage(err), 'danger');
        }
      }}>
        <label className="check"><input type="checkbox" disabled={!editable} checked={values.allow_self_enrollment} onChange={(event) => setValues({ ...values, allow_self_enrollment: event.target.checked })} /> {t('common.selfEnroll')}</label>
        <label className="check"><input type="checkbox" disabled={!editable} checked={values.require_enrollment_approval} onChange={(event) => setValues({ ...values, require_enrollment_approval: event.target.checked })} /> {t('common.approval')}</label>
        <label className="check"><input type="checkbox" disabled={!editable} checked={values.allow_waitlist} onChange={(event) => setValues({ ...values, allow_waitlist: event.target.checked })} /> {t('common.waitlistCeiling')}</label>
        <label className="check"><input type="checkbox" disabled={!editable} checked={values.allow_student_refund_requests} onChange={(event) => setValues({ ...values, allow_student_refund_requests: event.target.checked })} /> {t('common.studentRefunds')}</label>
        <label className="check"><input type="checkbox" disabled={!editable} checked={values.allow_finance_refund_requests} onChange={(event) => setValues({ ...values, allow_finance_refund_requests: event.target.checked })} /> {t('common.financeRefunds')}</label>
        <Field label={t('common.maxInstallments')}>
          <Select disabled={!editable} value={values.max_installments} onChange={(event) => setValues({ ...values, max_installments: Number(event.target.value) })}>
            <option value={1}>1</option><option value={2}>2</option><option value={3}>3</option>
          </Select>
        </Field>
        {editable ? <Button type="submit">{t('common.save')}</Button> : null}
      </form>
      <PolicyFacts centerId={centerId} />
    </Card>
  );
}

function PolicyFacts({ centerId }) {
  const { t } = useTranslation();
  const [rules, setRules] = useState(null);
  useEffect(() => {
    const path = centerId ? `/settings/effective/?center=${centerId}` : '/settings/effective/';
    client.get(path).then((response) => setRules(unwrap(response).rules)).catch(() => setRules(null));
  }, [centerId]);
  if (!rules) return null;
  return (
    <div style={{ marginTop: 16 }}>
      <h3>{t('common.effectivePolicy')}</h3>
      {Object.entries(rules).filter(([key]) => key !== 'defaults').map(([key, rule]) => (
        <p key={key}>
          <strong>{key}</strong>: {String(rule.effective)} · {rule.source} · {rule.effect}
        </p>
      ))}
    </div>
  );
}
