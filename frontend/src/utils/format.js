export function formatDateTime(value) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDate(value) {
  if (!value) {
    return "—";
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value));
  if (!match) {
    return "—";
  }
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

export function calendarDay(weekday) {
  return (Number(weekday) + 1) % 7;
}

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function weekdayName(weekday) {
  return WEEKDAYS[weekday] || "—";
}

export function seatSummary(active, capacity, waiting) {
  const seats = `${active} of ${capacity} seats filled`;
  return waiting ? `${seats}, ${waiting} waiting` : seats;
}

export function roleLabel(name) {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
