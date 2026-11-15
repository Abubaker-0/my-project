export function EmptyState({ title, body }) {
  return (
    <div className="px-6 py-12 text-center">
      <p className="font-serif text-xl text-ink-950">{title}</p>
      {body ? <p className="mx-auto mt-2 max-w-md text-sm text-ink-700">{body}</p> : null}
    </div>
  );
}
