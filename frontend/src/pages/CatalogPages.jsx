/**
 * Student course lists. Available courses exclude open enrollments.
 * My courses are the student's own enrollment history.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useToast } from '../context/ToastContext';
import { Badge, Button, Card, EmptyState, Loader } from '../components/ui';
import { DAYS, money, personName } from '../utils/format';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';

export function AvailableCoursesPage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    client.get('/courses/?available=1&page_size=100')
      .then((response) => {
        const data = unwrap(response);
        setRows(data.results || data);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);
  if (error) return <div className="error-state">{error}</div>;
  if (!rows) return <Loader label={t('common.loading')} />;
  if (!rows.length) return <EmptyState title={t('common.empty')} text="" />;
  return (
    <div>
      <div className="page-head"><h2>{t('nav.availableCourses')}</h2></div>
      <div className="course-grid">
        {rows.map((course) => (
          <Card key={course.id} className="course-card">
            <Badge value={course.status} label={t(`status.${course.status}`)} />
            <h3>{course.name}</h3>
            <p className="muted">{course.description}</p>
            <div className="meta">
              <span>{personName(course.teacher)}</span>
              <span>{money(course.fee)}</span>
              <span>{course.remaining_capacity} {t('common.seats')}</span>
            </div>
            {(course.schedules || []).slice(0, 2).map((slot) => (
              <div key={slot.id} className="muted">{t(`days.${DAYS[slot.day_of_week]}`)} {String(slot.start_time).slice(0, 5)}</div>
            ))}
            <Link className="btn" to={`/courses/${course.id}`} style={{ marginTop: 12 }}>{t('common.view')}</Link>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function MyCoursesPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const list = usePaged('/enrollments/');
  return (
    <div>
      <div className="page-head"><h2>{t('nav.myCourses')}</h2></div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'course', label: t('common.course'), render: (row) => <Link to={`/courses/${row.course?.id}`}>{row.course?.name}</Link> },
          { key: 'class', label: t('common.class'), render: (row) => row.course_class?.name },
          { key: 'source', label: t('common.type'), render: (row) => t(`common.${row.source}`) },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
          { key: 'date', label: t('common.date'), render: (row) => String(row.created_at || '').slice(0, 10) },
          { key: 'actions', label: t('common.actions'), render: (row) => row.status === 'active' ? (
            <Button variant="ghost" onClick={async () => {
              const reason = window.prompt(t('common.withdrawReason'));
              if (!reason) return;
              try {
                await client.post(`/enrollments/${row.id}/withdraw/`, { reason });
                toast(t('common.saved'), 'success');
                list.reload();
              } catch (err) {
                toast(errorMessage(err), 'danger');
              }
            }}>{t('common.withdraw')}</Button>
          ) : null },
        ]}
      />
    </div>
  );
}
