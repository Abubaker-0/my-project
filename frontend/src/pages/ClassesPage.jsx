/**
 * Class sections, rooms, and extra meeting times.
 * The manager creates them. Teachers see only the sections assigned to them.
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useOptions } from '../hooks/useOptions';
import { usePaged } from '../hooks/usePaged';
import { DataTable } from '../components/DataTable';
import { Button, Drawer, Field, Input, Modal, Select } from '../components/ui';
import { DAYS, personName } from '../utils/format';

export function ClassesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const list = usePaged('/classes/');
  const rooms = usePaged('/classes/classrooms/');
  const [open, setOpen] = useState(false);
  const [roomOpen, setRoomOpen] = useState(false);
  const [slotOpen, setSlotOpen] = useState(null);
  const [students, setStudents] = useState(null);
  const courses = useOptions(user?.role === 'center_manager' ? '/courses/' : '');
  const teachers = useOptions(user?.role === 'center_manager' ? '/users/?role=teacher' : '');
  const roomOptions = useOptions('/classes/classrooms/');
  const form = useForm({ defaultValues: { day_of_week: 0, start_time: '10:00', end_time: '11:30' } });
  const manager = user?.role === 'center_manager';

  return (
    <div className="grid">
      <div className="page-head">
        <h2>{t('nav.classes')}</h2>
        {manager ? (
          <div className="row-actions">
            <Button variant="ghost" onClick={() => setRoomOpen(true)}>{t('pages.newRoom')}</Button>
            <Button onClick={() => setOpen(true)}>{t('pages.newClass')}</Button>
          </div>
        ) : null}
      </div>
      <DataTable
        {...list}
        onPage={list.setPage}
        onSort={list.setOrdering}
        columns={[
          { key: 'name', label: t('common.class') },
          { key: 'course', label: t('common.course'), render: (row) => row.course_name },
          { key: 'teacher', label: t('common.teacher'), render: (row) => personName(row.teacher) },
          { key: 'students', label: t('nav.students'), render: (row) => row.student_count },
          { key: 'when', label: t('common.schedule'), render: (row) => (row.schedules || []).map((slot) => `${t(`days.${DAYS[slot.day_of_week]}`)} ${String(slot.start_time).slice(0, 5)}`).join(', ') },
          { key: 'actions', label: t('common.actions'), render: (row) => (
            <div className="row-actions">
              <Button variant="ghost" onClick={async () => {
                const response = await client.get(`/classes/${row.id}/students/`);
                setStudents({ title: row.name, rows: unwrap(response) });
              }}>{t('common.view')}</Button>
              {manager ? <Button variant="ghost" onClick={() => setSlotOpen(row)}>{t('common.addSchedule')}</Button> : null}
            </div>
          ) },
        ]}
      />
      {manager ? (
        <>
          <h3>{t('common.classroom')}</h3>
          <DataTable
            {...rooms}
            onPage={rooms.setPage}
            columns={[
              { key: 'name', label: t('common.name') },
              { key: 'capacity', label: t('common.capacity') },
            ]}
          />
        </>
      ) : null}
      <Modal title={t('pages.newClass')} open={open} onClose={() => setOpen(false)}>
        <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
          try {
            await client.post('/classes/', {
              course: Number(values.course),
              name: values.name,
              teacher: Number(values.teacher),
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
          <Field label={t('common.course')}>
            <Select {...form.register('course', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {courses.map((course) => <option key={course.id} value={course.id}>{course.name}</option>)}
            </Select>
          </Field>
          <Field label={t('common.name')}><Input {...form.register('name', { required: true })} /></Field>
          <Field label={t('common.teacher')}>
            <Select {...form.register('teacher', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{personName(teacher)}</option>)}
            </Select>
          </Field>
          <Field label={t('common.classroom')}>
            <Select {...form.register('classroom', { required: true })}>
              <option value="">{t('common.choose')}</option>
              {roomOptions.map((room) => <option key={room.id} value={room.id}>{room.name}</option>)}
            </Select>
          </Field>
          <Field label={t('common.day')}>
            <Select {...form.register('day_of_week')}>{DAYS.map((day, index) => <option key={day} value={index}>{t(`days.${day}`)}</option>)}</Select>
          </Field>
          <Field label={t('common.start')}><Input type="time" {...form.register('start_time')} /></Field>
          <Field label={t('common.end')}><Input type="time" {...form.register('end_time')} /></Field>
          <div className="row-actions wide"><Button type="submit">{t('common.create')}</Button></div>
        </form>
      </Modal>
      <Modal title={t('pages.newRoom')} open={roomOpen} onClose={() => setRoomOpen(false)}>
        <form className="grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          try {
            await client.post('/classes/classrooms/', { name: data.get('name'), capacity: Number(data.get('capacity')) });
            toast(t('common.created'), 'success');
            setRoomOpen(false);
            rooms.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.name')}><Input name="name" required /></Field>
          <Field label={t('common.capacity')}><Input name="capacity" type="number" min="1" required /></Field>
          <Button type="submit">{t('common.create')}</Button>
        </form>
      </Modal>
      <Modal title={t('common.addSchedule')} open={Boolean(slotOpen)} onClose={() => setSlotOpen(null)}>
        <form className="form-grid" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          try {
            await client.post(`/classes/${slotOpen.id}/schedules/`, {
              day_of_week: Number(data.get('day')),
              start_time: data.get('start'),
              end_time: data.get('end'),
              classroom: Number(data.get('room')),
            });
            toast(t('common.saved'), 'success');
            setSlotOpen(null);
            list.reload();
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.day')}>
            <Select name="day">{DAYS.map((day, index) => <option key={day} value={index}>{t(`days.${day}`)}</option>)}</Select>
          </Field>
          <Field label={t('common.classroom')}>
            <Select name="room">{roomOptions.map((room) => <option key={room.id} value={room.id}>{room.name}</option>)}</Select>
          </Field>
          <Field label={t('common.start')}><Input type="time" name="start" defaultValue="14:00" required /></Field>
          <Field label={t('common.end')}><Input type="time" name="end" defaultValue="15:30" required /></Field>
          <div className="row-actions wide"><Button type="submit">{t('common.save')}</Button></div>
        </form>
      </Modal>
      <Drawer title={students?.title || t('common.studentsInClass')} open={Boolean(students)} onClose={() => setStudents(null)}>
        {(students?.rows || []).map((student) => <p key={student.id}>{personName(student)}</p>)}
        {students && !students.rows.length ? <p className="muted">{t('common.empty')}</p> : null}
      </Drawer>
    </div>
  );
}
