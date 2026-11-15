/**
 * Course catalog. Super admin can read every center and cannot create.
 * A course is created with its first section and at least one schedule.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Badge, Button, Field, Input, Modal, SearchInput, Select, TextArea } from '../components/ui';
import { DAYS, addDays, money, personName, todayISO } from '../utils/format';

export function CoursesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/courses/');
  const [open, setOpen] = useState(false);
  const teachers = useOptions(open ? '/users/?role=teacher' : '');
  const rooms = useOptions(open ? '/classes/classrooms/' : '');
  const form = useForm({
    defaultValues: {
      duration_hours: 48,
      capacity: 20,
      fee: '1000',
      start_date: todayISO(),
      end_date: addDays(todayISO(), 90),
      section_name: 'Section A',
      day_of_week: 0,
      start_time: '08:00',
      end_time: '09:30',
    },
  });
  const manager = user?.role === 'center_manager';
  return (
    <div>
      <div className="page-head">
        <div>
          <h2>{t('nav.courses')}</h2>
          {user?.role === 'super_admin' ? <p>{t('common.superCourseHint')}</p> : null}
        </div>
        {manager ? <Button onClick={() => setOpen(true)}>{t('pages.newCourse')}</Button> : null}
      </div>
      <div className="toolbar">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder={t('common.search')} />
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        onSort={list.setOrdering}
        columns={[
          { key: 'name', label: t('common.name'), sort: 'name', render: (row) => <Link to={`/courses/${row.id}`}>{row.name}</Link> },
          { key: 'code', label: t('common.code') },
          { key: 'teacher', label: t('common.teacher'), render: (row) => personName(row.teacher) },
          { key: 'fee', label: t('common.fee'), sort: 'fee', render: (row) => money(row.fee) },
          { key: 'capacity', label: t('common.capacity'), render: (row) => `${row.remaining_capacity}/${row.capacity}` },
          { key: 'status', label: t('common.status'), render: (row) => <Badge value={row.status} label={t(`status.${row.status}`)} /> },
        ]}
      />
      <Modal title={t('pages.newCourse')} open={open} onClose={() => setOpen(false)}>
        <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
          try {
            await client.post('/courses/', {
              name: values.name,
              code: values.code,
              description: values.description,
              teacher: Number(values.teacher),
              duration_hours: Number(values.duration_hours),
              start_date: values.start_date,
              end_date: values.end_date,
              fee: values.fee,
              capacity: Number(values.capacity),
              section_name: values.section_name,
              schedules: [{
                day_of_week: Number(values.day_of_week),
                start_time: values.start_time,
                end_time: values.end_time,
                classroom: Number(values.classroom),
              }],
            });
            toast(t('common.created'), 'success');
            setOpen(false);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        })}>
          <Field label={t('common.name')}><Input {...form.register('name', { required: true })} /></Field>
          <Field label={t('common.code')}><Input {...form.register('code')} /></Field>
          <Field className="wide" label={t('common.description')}><TextArea {...form.register('description', { required: true })} /></Field>
          <Field label={t('common.teacher')}>
            <Select {...form.register('teacher', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{personName(teacher)}</option>)}
            </Select>
          </Field>
          <Field label={t('common.classroom')}>
            <Select {...form.register('classroom', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {rooms.map((room) => <option key={room.id} value={room.id}>{room.name}</option>)}
            </Select>
          </Field>
          <Field label={t('common.fee')}><Input type="number" step="0.01" {...form.register('fee')} /></Field>
          <Field label={t('common.capacity')}><Input type="number" {...form.register('capacity')} /></Field>
          <Field label={t('common.duration')}><Input type="number" {...form.register('duration_hours')} /></Field>
          <Field label={t('common.section')}><Input {...form.register('section_name')} /></Field>
          <Field label={t('common.start')}><Input type="date" {...form.register('start_date')} /></Field>
          <Field label={t('common.end')}><Input type="date" {...form.register('end_date')} /></Field>
          <Field label={t('common.day')}>
            <Select {...form.register('day_of_week')}>
              {DAYS.map((day, index) => <option key={day} value={index}>{t(`days.${day}`)}</option>)}
            </Select>
          </Field>
          <Field label={t('common.start')}><Input type="time" {...form.register('start_time')} /></Field>
          <Field label={t('common.end')}><Input type="time" {...form.register('end_time')} /></Field>
          <div className="row-actions wide"><Button type="submit">{t('common.create')}</Button></div>
        </form>
      </Modal>
    </div>
  );
}
