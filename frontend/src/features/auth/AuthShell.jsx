import { Link } from "react-router-dom";

export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-pine-900 px-12 py-10 text-paper lg:flex">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pine-50/80">
            Tuition Center
          </p>
          <h1 className="mt-6 max-w-md font-serif text-5xl leading-tight">
            One record for every campus, class, and fee.
          </h1>
        </div>
        <ul className="max-w-sm space-y-3 text-sm text-pine-50/90">
          <li>Branch-scoped access from the first sign-in.</li>
          <li>Short-lived access tokens and rotating refresh sessions.</li>
          <li>Every sign-in, change, and permission edit is audited.</li>
        </ul>
      </section>
      <section className="flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <Link to="/login" className="font-serif text-2xl text-ink-950 lg:hidden">
            Tuition Center
          </Link>
          <h2 className="mt-6 font-serif text-4xl">{title}</h2>
          <p className="mt-2 text-sm text-ink-700">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </div>
  );
}
