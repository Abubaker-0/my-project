/**
 * Role dashboard. The figures come from /reports/dashboard/, which already
 * limits each role to their own center and their own classes.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Area, AreaChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Banknote, BookOpen, Building2, GraduationCap, Users, Wallet } from 'lucide-react';
import client, { errorMessage, unwrap } from '../api/client';
import { ChartCard, EmptyState, Loader, StatCard } from '../components/ui';
import { money } from '../utils/format';

const ICONS = {
  centers: <Building2 size={18} />,
  students: <GraduationCap size={18} />,
  teachers: <Users size={18} />,
  courses: <BookOpen size={18} />,
  classes: <BookOpen size={18} />,
  collected: <Wallet size={18} />,
  outstanding: <Banknote size={18} />,
  refunds: <Banknote size={18} />,
  overdue: <Banknote size={18} />,
  present: <Users size={18} />,
  absent: <Users size={18} />,
};

export function DashboardPage() {
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    client.get('/reports/dashboard/').then((response) => setData(unwrap(response))).catch((err) => setError(errorMessage(err)));
  }, []);
  if (error) return <div className="error-state">{error}</div>;
  if (!data) return <Loader label={t('common.loading')} />;
  const currency = data.currency || 'AFN';
  const monthly = (data.monthly_revenue || []).map((row) => ({ ...row, total: Number(row.total) }));
  const methods = (data.payment_methods || []).map((row) => ({ name: t(`common.${row.method}`), total: Number(row.total) }));
  return (
    <div className="grid">
      {(data.alerts || []).map((alert) => (
        <div className="alert" key={alert.code}>{t(`alerts.${alert.code}`)} · {alert.count}</div>
      ))}
      <section className="grid stats">
        {(data.kpis || []).map((kpi) => (
          <StatCard
            key={kpi.key}
            label={t(`kpi.${kpi.key}`)}
            value={['collected', 'outstanding'].includes(kpi.key) ? money(kpi.value, currency) : kpi.value}
            icon={ICONS[kpi.key]}
          />
        ))}
      </section>
      <section className="grid split">
        <ChartCard title={t('common.revenue')}>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthly}>
                <XAxis dataKey="month" stroke="currentColor" fontSize={12} />
                <YAxis stroke="currentColor" fontSize={12} />
                <Tooltip />
                <Area type="monotone" dataKey="total" stroke="var(--primary)" fill="var(--primary-soft)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
        <ChartCard title={t('common.methods')}>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={methods}>
                <XAxis dataKey="name" stroke="currentColor" fontSize={12} />
                <YAxis stroke="currentColor" fontSize={12} />
                <Tooltip />
                <Bar dataKey="total" fill="var(--accent)" radius={8} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </section>
      <section className="grid split">
        <ChartCard title={t('common.scheduleToday')}>
          {(data.today_schedule || []).length === 0 ? <EmptyState title={t('common.noSchedule')} text="" /> : (
            data.today_schedule.map((slot) => (
              <div className="slot" key={slot.id}>
                <strong>{slot.start_time}–{slot.end_time}</strong> {slot.course}
                <div className="muted">{slot.class_name} · {slot.teacher} · {slot.classroom}</div>
              </div>
            ))
          )}
        </ChartCard>
        <ChartCard title={t('common.contract')}>
          {data.contract ? (
            <div className="grid">
              <div>{t(`common.${data.contract.contract_type}`)} · {t(`status.${data.contract.status}`)}</div>
              <div>{data.contract.start_date} → {data.contract.end_date}</div>
              <div>{t(`common.${data.contract.salary_type}`)} · {money(data.contract.salary_amount, currency)}</div>
              <div>{t(`common.${data.contract.payment_method}`)}</div>
            </div>
          ) : <EmptyState title={t('common.noContract')} text="" />}
          <p className="muted" style={{ marginTop: 12 }}>
            {t('common.attendance')}: {data.attendance?.present || 0} / {data.attendance?.absent || 0}
            {' · '}
            {t('common.enrollment')}: {data.enrollment?.active || 0}
          </p>
        </ChartCard>
      </section>
      {data.center_rows?.length ? (
        <ChartCard title={t('common.centersOverview')}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t('common.name')}</th>
                  <th>{t('kpi.students')}</th>
                  <th>{t('kpi.teachers')}</th>
                  <th>{t('kpi.courses')}</th>
                  <th>{t('common.collected')}</th>
                  <th>{t('common.outstanding')}</th>
                </tr>
              </thead>
              <tbody>
                {data.center_rows.map((row) => (
                  <tr key={row.id}>
                    <td><Link to={`/centers/${row.id}`}>{row.name}</Link></td>
                    <td>{row.students}</td>
                    <td>{row.teachers}</td>
                    <td>{row.courses}</td>
                    <td>{money(row.collected, currency)}</td>
                    <td>{money(row.outstanding, currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
      ) : null}
    </div>
  );
}
