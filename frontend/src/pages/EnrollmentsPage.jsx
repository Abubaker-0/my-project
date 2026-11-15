/**
 * Enrollment desk for the center manager.
 * Manual enrollment still checks capacity, duplicates, and schedule clashes.
 */
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Badge, Button, Card, Field, FilterDropdown, Modal, Select } from '../components/ui';
import { personName } from '../utils/format';

export function EnrollmentsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const list = usePaged('/enrollments/');
  const [open, setOpen] = useState(false);
  const students = useOptions(open ? '/users/?role=student' : '');
  const courses = useOptions(open ? '/courses/' : '');
  const form = useForm();
  const courseId = form.watch('course_id');
  const selected = courses.find((course) => String(course.id) === String(courseId));
  return (
    <div>
      <div className="page-head">
        <h2>{t('nav.enrollments')}</h2>
        <Button onClick={() => setOpen(true)}>{t('pages.manualEnroll')}</Button>
      </div>
      <div className="toolbar">
        <FilterDropdown
          label={t('common.status')}
          value={list.filters.status || ''}
          onChange={(value) => list.setFilters({ status: value })}
          options={[
            { value: '', label: t('common.all') },
            ...['pending', 'active', 'rejected', 'cancelled', 'dropped'].map((status) => ({ value: status, label: t(`status.${status}`) })),
          ]}
        />
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        columns={[
          { key: 'student', label: t('common.student'), render: (row) => personName(row.student) },
          { key: 'course', label: t('common.course'), render: (row) => row.course?.name },
          { key: 'class', label: t('common.class'), render: (row) => row.course_class?.name },
          { key: 'source', label: t('common.type'), render: (row) => t(`common.${row.source}`) },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
          { key: 'actions', label: t('common.actions'), render: (row) => row.status === 'pending' ? (
            <div className="row-actions">
              <Button onClick={() => decide(row.id, 'approve')}>{t('common.approve')}</Button>
              <Button variant="danger" onClick={() => decide(row.id, 'reject')}>{t('common.reject')}</Button>
            </div>
          ) : row.status === 'active' ? (
            <Button variant="ghost" onClick={() => {
              client.post(`/enrollments/${row.id}/complete/`, {}).then(() => {
                toast(t('common.saved'), 'success');
                list.reload();
              }).catch((err) => toast(errorMessage(err), 'danger'));
            }}>{t('common.complete')}</Button>
          ) : null },
        ]}
      />
      <WaitlistPanel />
      <Modal title={t('pages.manualEnroll')} open={open} onClose={() => setOpen(false)}>
        <form className="grid" onSubmit={form.handleSubmit(async (values) => {
          try {
            await client.post('/enrollments/manual/', {
              student_id: Number(values.student_id),
              course_id: Number(values.course_id),
              class_id: Number(values.class_id),
            });
            toast(t('common.saved'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field label={t('common.student')}>
            <Select {...form.register('student_id', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {students.map((student) => <option key={student.id} value={student.id}>{personName(student)}</option>)}
            </Select>
          </Field>
          <Field label={t('common.course')}>
            <Select {...form.register('course_id', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {courses.map((course) => <option key={course.id} value={course.id}>{course.name} · {course.remaining_capacity}</option>)}
            </Select>
          </Field>
          <Field label={t('common.class')}>
            <Select {...form.register('class_id', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {(selected?.classes || []).map((courseClass) => <option key={courseClass.id} value={courseClass.id}>{courseClass.name}</option>)}
            </Select>
          </Field>
          <Button type="submit">{t('common.enroll')}</Button>
        </form>
      </Modal>
    </div>
  );

  function decide(id, action) {
    client.post(`/enrollments/${id}/${action}/`, {}).then(() => {
      toast(t('common.saved'), 'success');
      list.reload();
    }).catch((err) => toast(errorMessage(err), 'danger'));
  }
}

function WaitlistPanel() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [requests, setRequests] = useState([]);
  const load = () => {
    client.get('/enrollments/waitlist/').then((response) => setRows(unwrap(response) || [])).catch(() => setRows([]));
    client.get('/enrollments/withdrawals/').then((response) => setRequests(unwrap(response) || [])).catch(() => setRequests([]));
  };
  useEffect(load, []);
  const promote = (id) => {
    client.post('/enrollments/promote-waitlist/', { id }).then(() => {
      toast(t('common.saved'), 'success');
      load();
    }).catch((err) => toast(errorMessage(err), 'danger'));
  };
  const decide = (id, approve) => {
    client.post('/enrollments/decide-withdrawal/', { id, approve, note: approve ? 'Approved by the centre manager.' : 'Rejected by the centre manager.' }).then(() => {
      toast(t('common.saved'), 'success');
      load();
    }).catch((err) => toast(errorMessage(err), 'danger'));
  };
  return (
    <div className="grid" style={{ marginTop: 16 }}>
      <Card>
        <h3>{t('common.joinWaitlist')}</h3>
        {rows.filter((row) => row.status === 'waiting').map((row) => (
          <div className="row-actions" key={row.id}>
            <span>{row.student} — {row.course}</span>
            <Button onClick={() => promote(row.id)}>{t('common.promote')}</Button>
          </div>
        ))}
      </Card>
      <Card>
        <h3>{t('common.withdraw')}</h3>
        {requests.filter((row) => row.status === 'pending').map((row) => (
          <div className="row-actions" key={row.id}>
            <span>{row.student} — {row.reason}</span>
            <Button onClick={() => decide(row.id, true)}>{t('common.approve')}</Button>
            <Button variant="danger" onClick={() => decide(row.id, false)}>{t('common.reject')}</Button>
          </div>
        ))}
      </Card>
    </div>
  );
}
