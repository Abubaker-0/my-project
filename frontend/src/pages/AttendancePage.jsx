/**
 * Attendance register.
 * Teachers submit present or absent for their own class. After submission
 * only the center manager can correct a mark.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Badge, Button, Field, Input, Select } from '../components/ui';
import { personName, todayISO } from '../utils/format';

export function AttendancePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const classes = useOptions('/classes/?page_size=100');
  const history = usePaged('/attendance/');
  const [classId, setClassId] = useState('');
  const [date, setDate] = useState(todayISO());
  const [roster, setRoster] = useState(null);
  const [marks, setMarks] = useState({});
  const [reason, setReason] = useState('');

  const loadRoster = async (event) => {
    event?.preventDefault();
    try {
      const response = await client.get(`/attendance/roster/?class_id=${classId}&date=${date}`);
      const data = unwrap(response);
      setRoster(data);
      const next = {};
      data.students.forEach((row) => { next[row.student.id] = row.status || 'present'; });
      setMarks(next);
    } catch (err) {
      toast(errorMessage(err), 'danger');
    }
  };

  const submit = async () => {
    try {
      if (roster.submitted && user.role === 'center_manager') {
        await Promise.all(roster.students.filter((row) => row.record_id).map((row) => (
          client.patch(`/attendance/records/${row.record_id}/`, { status: marks[row.student.id], reason })
        )));
      } else {
        await client.post('/attendance/mark/', {
          class_id: Number(classId),
          date,
          records: roster.students.map((row) => ({ student_id: row.student.id, status: marks[row.student.id] })),
        });
      }
      toast(t('common.saved'), 'success');
      history.reload();
      loadRoster();
    } catch (err) {
      toast(errorMessage(err), 'danger');
    }
  };

  return (
    <div className="grid">
      <div className="page-head"><h2>{t('nav.attendance')}</h2></div>
      {user?.role !== 'student' ? (
        <form className="toolbar" onSubmit={loadRoster}>
          <Field label={t('common.class')}>
            <Select value={classId} onChange={(event) => setClassId(event.target.value)} required>
              <option value="">{t('common.choose')}</option>
              {classes.map((courseClass) => <option key={courseClass.id} value={courseClass.id}>{courseClass.course_name} · {courseClass.name}</option>)}
            </Select>
          </Field>
          <Field label={t('common.date')}><Input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></Field>
          <Button type="submit">{t('common.view')}</Button>
        </form>
      ) : null}
      {roster ? (
        <div className="card">
          <h3>{roster.submitted ? t('status.submitted_to_manager') : t('common.mark')}</h3>
          {roster.students.map((row) => (
            <div className="row-actions" key={row.student.id} style={{ marginTop: 10 }}>
              <strong style={{ minWidth: 180 }}>{personName(row.student)}</strong>
              {['present', 'absent'].map((status) => (
                <label key={status} className="check">
                  <input
                    type="radio"
                    name={`mark-${row.student.id}`}
                    checked={marks[row.student.id] === status}
                    disabled={roster.submitted && user.role !== 'center_manager'}
                    onChange={() => setMarks({ ...marks, [row.student.id]: status })}
                  />
                  {t(`common.${status}`)}
                </label>
              ))}
              {roster.submitted && user.role === 'teacher' && row.record_id ? (
                <Button variant="ghost" onClick={async () => {
                  const reason = window.prompt(t('common.correctionRequest'));
                  if (!reason) return;
                  try {
                    await client.post('/attendance/correction-requests/', {
                      record_id: row.record_id,
                      status: marks[row.student.id] || (row.status === 'present' ? 'absent' : 'present'),
                      reason,
                    });
                    toast(t('common.saved'), 'success');
                  } catch (err) {
                    toast(errorMessage(err), 'danger');
                  }
                }}>{t('common.requestCorrection')}</Button>
              ) : null}
            </div>
          ))}
          {!roster.students.length ? <p className="muted">{t('common.empty')}</p> : null}
          {roster.submitted && user.role === 'center_manager' ? (
            <Field label={t('common.reason')}><Input value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
          ) : null}
          {roster.students.length && (!roster.submitted || user.role === 'center_manager') ? (
            <Button onClick={submit} style={{ marginTop: 14 }}>{roster.submitted ? t('common.correct') : t('common.mark')}</Button>
          ) : null}
        </div>
      ) : null}
      <DataTable
        {...history}
        onPage={history.setPage}
        columns={[
          { key: 'date', label: t('common.date') },
          { key: 'class', label: t('common.class'), render: (row) => row.class_name },
          { key: 'count', label: t('nav.students'), render: (row) => (row.records || []).length },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value="active" label={row.is_submitted ? t('common.mark') : '—'} /> },
        ]}
      />
    </div>
  );
}
