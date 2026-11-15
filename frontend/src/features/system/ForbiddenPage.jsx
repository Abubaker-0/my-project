import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <div className="mx-auto max-w-lg py-16 text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-clay">403</p>
      <h1 className="mt-2 font-serif text-4xl">You do not have access to that page</h1>
      <p className="mt-3 text-sm text-ink-700">
        The menu only shows what your role allows. If you still need this page, ask a Super Admin to
        grant the permission.
      </p>
      <Link className="mt-6 inline-block text-sm text-pine-700" to="/">
        Back to the dashboard
      </Link>
    </div>
  );
}
