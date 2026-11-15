/**
 * Contract inputs shared by hiring and manager assignment.
 * Length is yearly (365 days) or six months (182 days), matching the API rule.
 */
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Field, Input, Select } from './ui';
import { addDays, todayISO } from '../utils/format';

export function ContractFields({ register, setValue, watch }) {
  const { t } = useTranslation();
  const kind = watch('contract.contract_type');
  const start = watch('contract.start_date');
  useEffect(() => {
    if (!start) return;
    setValue('contract.end_date', addDays(start, kind === 'six_months' ? 182 : 365));
  }, [kind, start, setValue]);
  return (
    <>
      <Field label={t('common.contractType')}>
        <Select {...register('contract.contract_type')}>
          <option value="yearly">{t('common.yearly')}</option>
          <option value="six_months">{t('common.six_months')}</option>
        </Select>
      </Field>
      <Field label={t('common.salaryType')}>
        <Select {...register('contract.salary_type')}>
          <option value="monthly">{t('common.monthly')}</option>
          <option value="hourly">{t('common.hourly')}</option>
        </Select>
      </Field>
      <Field label={t('common.start')}><Input type="date" {...register('contract.start_date')} /></Field>
      <Field label={t('common.end')}><Input type="date" {...register('contract.end_date')} /></Field>
      <Field label={t('common.salary')}><Input type="number" step="0.01" {...register('contract.salary_amount')} /></Field>
      <Field label={t('common.paymentMethod')}>
        <Select {...register('contract.payment_method')}>
          <option value="bank">{t('common.bank')}</option>
          <option value="cash">{t('common.cash')}</option>
        </Select>
      </Field>
    </>
  );
}

export const emptyContract = {
  contract_type: 'yearly',
  salary_type: 'monthly',
  start_date: todayISO(),
  end_date: addDays(todayISO(), 365),
  salary_amount: '25000',
  payment_method: 'bank',
};
