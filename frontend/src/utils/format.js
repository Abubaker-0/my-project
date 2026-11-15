/**
 * Display helpers shared by tables and dashboards.
 * Money stays a decimal string from the API and is only formatted here.
 */

export const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

export function money(value, currency = 'AFN') {
  const number = Number(value || 0);
  if (Number.isNaN(number)) return `${value} ${currency}`;
  return `${new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number)} ${currency}`;
}

export function personName(person) {
  if (!person) return '';
  return person.full_name || `${person.first_name || ''} ${person.last_name || ''}`.trim() || person.username || '';
}

export function todayISO() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

export function addDays(iso, days) {
  const date = new Date(`${iso}T00:00:00`);
  date.setDate(date.getDate() + days);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}
