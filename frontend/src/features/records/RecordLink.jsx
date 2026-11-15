import { Link } from "react-router-dom";

export function RecordLink({ to, children }) {
  return (
    <Link className="font-medium text-pine-800 underline-offset-2 hover:underline" to={to}>
      {children}
    </Link>
  );
}
