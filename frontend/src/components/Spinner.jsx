export function Spinner({ label = "Loading" }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-700" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-pine-700 border-t-transparent" />
      {label}
    </span>
  );
}

export function FullScreenLoader({ label = "Loading" }) {
  return (
    <div className="grid min-h-screen place-items-center bg-paper">
      <Spinner label={label} />
    </div>
  );
}
