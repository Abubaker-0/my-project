import { Navigate } from "react-router-dom";

import { usePermission } from "../hooks/usePermission";

export function RequirePermission({ permission, children }) {
  const allowed = usePermission(permission);
  if (!allowed) {
    return <Navigate to="/forbidden" replace />;
  }
  return children;
}
