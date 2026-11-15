import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="grid min-h-screen place-items-center bg-paper px-4">
      <div className="max-w-md text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-pine-700">404</p>
        <h1 className="mt-2 font-serif text-4xl">That page is not in this system</h1>
        <Link className="mt-6 inline-block text-sm text-pine-700" to="/">
          Go to the dashboard
        </Link>
      </div>
    </div>
  );
}
