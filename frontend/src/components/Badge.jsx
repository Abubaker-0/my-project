const TONES = {
  neutral: "bg-paper text-ink-700",
  good: "bg-pine-50 text-pine-800",
  warn: "bg-amber-100 text-amber-900",
  bad: "bg-red-100 text-danger",
};

export function Badge({ tone = "neutral", children }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function statusTone(status) {
  if (status === "active") return "good";
  if (status === "locked") return "warn";
  return "bad";
}
