/**
 * Course detail used by managers, teachers, and students.
 * Students enroll from here only when seats remain in their own center.
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Badge, Breadcrumbs, Button, Card } from '../components/ui';
import { DAYS, money, personName } from '../utils/format';

export function CourseDetailPage() {
  const { id } = useParams();
  const { t } = useTranslation();
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  useEffect(() => {
    client.get(`/courses/${id}/`).then((response) => setCourse(unwrap(response))).catch((err) => toast(errorMessage(err), 'danger'));
  }, [id]);
  if (!course) return null;
  const section = course.classes?.[0];
  return (
    <div className="grid">
      <Breadcrumbs items={[{ to: user?.role === 'student' ? '/available-courses' : '/courses', label: t('nav.courses') }, { label: course.name }]} />
      <div className="page-head">
        <div>
          <h2>{course.name}</h2>
          <p>{course.code} · {course.center?.name}</p>
        </div>
        <Badge value={course.status} label={t(`status.${course.status}`)} />
      </div>
      <div className="grid split">
        <Card>
          <p>{course.description}</p>
          <div className="meta">
            <span>{t('common.teacher')}: {personName(course.teacher)}</span>
            <span>{t('common.fee')}: {money(course.fee)}</span>
            <span>{t('common.duration')}: {course.duration_hours}</span>
            <span>{course.start_date} → {course.end_date}</span>
            <span>{t('common.remaining')}: {course.remaining_capacity} {t('common.seats')}</span>
          </div>
          {(course.schedules || []).map((slot) => (
            <div className="slot" key={slot.id}>
              {t(`days.${DAYS[slot.day_of_week]}`)} · {String(slot.start_time).slice(0, 5)}–{String(slot.end_time).slice(0, 5)} · {slot.classroom_name}
            </div>
          ))}
        </Card>
        <Card>
          <h3>{t('common.actions')}</h3>
          {user?.role === 'center_manager' ? (
            <div className="row-actions">
              <Button variant="ghost" onClick={async () => {
                try {
                  const action = course.status === 'active' ? 'deactivate' : 'activate';
                  const response = await client.post(`/courses/${course.id}/${action}/`);
                  setCourse(unwrap(response));
                } catch (err) {
                  toast(errorMessage(err), 'danger');
                }
              }}>{course.status === 'active' ? t('common.deactivate') : t('common.activate')}</Button>
            </div>
          ) : null}
          {user?.role === 'student' && section ? (
            <Button disabled={course.remaining_capacity < 1} onClick={async () => {
              try {
                await client.post('/enrollments/self-enroll/', { course_id: course.id, class_id: section.id });
                toast(t('common.saved'), 'success');
                navigate('/my-courses');
              } catch (err) {
                toast(errorMessage(err), 'danger');
              }
            }}>{course.remaining_capacity < 1 ? t('common.capacityFull') : t('common.enroll')}</Button>
          ) : null}
          {user?.role === 'student' && section && course.remaining_capacity < 1 ? (
            <Button variant="ghost" onClick={async () => {
              try {
                await client.post('/enrollments/waitlist/', { course_id: course.id, class_id: section.id });
                toast(t('common.waitlistJoined'), 'success');
              } catch (err) {
                toast(errorMessage(err), 'danger');
              }
            }}>{t('common.joinWaitlist')}</Button>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
