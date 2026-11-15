/**
 * Weekly timetable built from the class sections the caller is allowed to see.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import client, { unwrap } from '../api/client';
import { DAYS, personName } from '../utils/format';
import { Loader } from '../components/ui';

export function SchedulePage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState(null);
  useEffect(() => {
    client.get('/classes/?page_size=100').then((response) => {
      const data = unwrap(response);
      setRows(data.results || data);
    }).catch(() => setRows([]));
  }, []);
  if (!rows) return <Loader label={t('common.loading')} />;
  const columns = DAYS.map((day, index) => ({
    day,
    slots: rows.flatMap((courseClass) => (courseClass.schedules || [])
      .filter((slot) => slot.day_of_week === index)
      .map((slot) => ({ ...slot, course: courseClass.course_name, teacher: personName(courseClass.teacher), section: courseClass.name }))),
  }));
  return (
    <div>
      <div className="page-head"><h2>{t('nav.schedule')}</h2></div>
      <div className="week">
        {columns.map((column) => (
          <section className="day-col" key={column.day}>
            <h3>{t(`days.${column.day}`)}</h3>
            {column.slots.sort((a, b) => String(a.start_time).localeCompare(String(b.start_time))).map((slot) => (
              <div className="slot" key={slot.id}>
                <strong>{String(slot.start_time).slice(0, 5)}–{String(slot.end_time).slice(0, 5)}</strong>
                <div>{slot.course}</div>
                <div className="muted">{slot.section} · {slot.classroom_name}</div>
                <div className="muted">{slot.teacher}</div>
              </div>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
