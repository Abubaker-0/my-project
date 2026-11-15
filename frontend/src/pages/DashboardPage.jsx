/**
 * Role overview built only from /reports/dashboard/ and, where permitted,
 * enrollments and the audit log. Missing figures stay empty.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Banknote, BookOpen, Building2, CalendarDays, GraduationCap, Users, Wallet } from 'lucide-react';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Badge, EmptyState, Loader } from '../components/ui';
import { money, personName } from '../utils/format';

const ICONS = {
  centers: Building2,
  students: GraduationCap,
  teachers: Users,
  courses: BookOpen,
  classes: BookOpen,
  collected: Wallet,
  outstanding: Banknote,
  refunds: Banknote,
  overdue: Banknote,
  present: Users,
  absent: Users,
};

function greetingKey() {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
}

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { resolved, palette } = useTheme();
  const [barFill, setBarFill] = useState('#28594F');
  useEffect(() => {
    const value = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
    if (value) setBarFill(value);
  }, [resolved, palette]);
  const [data, setData] = useState(null);
  const [rows, setRows] = useState([]);
  const [activity, setActivity] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    client.get('/reports/dashboard/')
      .then((response) => { if (!cancelled) setData(unwrap(response)); })
      .catch((err) => { if (!cancelled) setError(errorMessage(err)); });
    client.get('/enrollments/?page_size=5&ordering=-created_at')
      .then((response) => { if (!cancelled) setRows((unwrap(response).results) || []); })
      .catch(() => { if (!cancelled) setRows([]); });
    if (['super_admin', 'center_manager'].includes(user?.role)) {
      client.get('/reports/audit-logs/?page_size=4&ordering=-created_at')
        .then((response) => { if (!cancelled) setActivity((unwrap(response).results) || []); })
        .catch(() => { if (!cancelled) setActivity([]); });
    }
    return () => { cancelled = true; };
  }, [user?.role]);

  if (error) return <div className="error-state">{error}</div>;
  if (!data) return <Loader label={t('common.loading')} />;

  const currency = data.currency || 'AFN';
  const monthly = (data.monthly_revenue || []).map((row) => ({ ...row, total: Number(row.total) }));
  const present = data.attendance?.present || 0;
  const absent = data.attendance?.absent || 0;
  const rate = present + absent ? `${Math.round((present / (present + absent)) * 1000) / 10}%` : '—';
  const first = user?.first_name || personName(user);
  const cards = [...(data.kpis || [])];
  if (present + absent) cards.push({ key: 'rate', value: rate, foot: t('dash.rateFoot') });
  const dateLabel = new Intl.DateTimeFormat(i18n.language === 'fa' ? 'fa-AF' : 'en', { dateStyle: 'medium' }).format(new Date());

  return (
    <div className="grid">
      <div className="dash-heading page-head">
        <div>
          <div className="eyebrow">{t(`dash.eyebrow.${user?.role}`)}</div>
          <h2>{t(`dash.${greetingKey()}`, { name: first })}</h2>
          <p>{t(`dash.lead.${user?.role}`)}</p>
        </div>
        <span className="date-chip">{dateLabel}</span>
      </div>
      {(data.alerts || []).map((alert) => (
        <div className="alert" key={alert.code}>{t(`alerts.${alert.code}`)} · {alert.count}</div>
      ))}
      <section className="grid kpi-grid">
        {cards.map((kpi) => {
          const Icon = ICONS[kpi.key] || BookOpen;
          const moneyKeys = ['collected', 'outstanding'];
          return (
            <article className="kpi" key={kpi.key}>
              <div className="kpi-top">
                <span>{kpi.key === 'rate' ? t('common.rate') : t(`kpi.${kpi.key}`)}</span>
                <span className="kpi-icon"><Icon size={16} /></span>
              </div>
              <div className="kpi-number">{moneyKeys.includes(kpi.key) ? money(kpi.value, currency) : kpi.value}</div>
              <div className="kpi-foot">{kpi.foot || t(`dash.foot.${kpi.key}`, { defaultValue: '' })}</div>
            </article>
          );
        })}
      </section>
      <section className="grid content-columns">
        <section className="panel">
          <div className="panel-heading">
            <h3>{t('dash.chart')}</h3>
            <small className="muted">{currency}</small>
          </div>
          <div style={{ height: 220 }}>
            {monthly.some((row) => row.total) ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthly}>
                  <XAxis dataKey="month" stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} width={48} />
                  <Tooltip
                    cursor={{ fill: 'transparent' }}
                    contentStyle={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12, color: 'var(--ink)' }}
                  />
                  <Bar dataKey="total" fill={barFill} radius={[7, 7, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState title={t('common.empty')} text="" />}
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading"><h3>{t('dash.activity')}</h3></div>
          {activity.length ? activity.map((item) => (
            <div className="activity-item" key={item.id}>
              <div>
                <strong>{item.message}</strong>
                <small>{String(item.created_at).slice(0, 16).replace('T', ' ')}</small>
              </div>
            </div>
          )) : (data.today_schedule || []).length ? data.today_schedule.map((slot) => (
            <div className="activity-item" key={slot.id}>
              <CalendarDays size={16} />
              <div>
                <strong>{slot.start_time}–{slot.end_time} · {slot.course}</strong>
                <small>{slot.class_name} · {slot.classroom}</small>
              </div>
            </div>
          )) : <EmptyState title={t('shell.emptyNotes')} text="" />}
          {data.contract ? (
            <p className="muted" style={{ marginTop: 12 }}>
              {t('common.contract')}: {t(`common.${data.contract.contract_type}`)} · {money(data.contract.salary_amount, currency)}
            </p>
          ) : null}
        </section>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h3>{user?.role === 'super_admin' ? t('dash.centres') : t('dash.registrations')}</h3>
          {user?.role !== 'super_admin' ? <Link to={user?.role === 'student' ? '/my-courses' : '/enrollments'}>{t('common.view')}</Link> : null}
        </div>
        {user?.role === 'super_admin' && data.center_rows?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t('common.center')}</th>
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
        ) : rows.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t('common.student')}</th>
                  <th>{t('common.course')}</th>
                  <th>{t('common.center')}</th>
                  <th>{t('common.status')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{personName(row.student)}</td>
                    <td>{row.course?.name}</td>
                    <td>{row.center?.name}</td>
                    <td><Badge value={row.status} label={t(`status.${row.status}`)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title={t('common.empty')} text="" />}
      </section>
    </div>
  );
}
