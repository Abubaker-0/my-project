export function Panel({ title, actions, children }) {
  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        {title ? <h2 className="font-serif text-xl">{title}</h2> : <span />}
        {actions}
      </div>
      {children}
    </section>
  );
}
