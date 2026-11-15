/** Hides a route from roles that are not in the allowed list. */
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function RoleGuard({ roles, children }) {
  const { user } = useAuth();
  if (!user) return null;
  if (roles && !roles.includes(user.role)) return <Navigate to="/forbidden" replace />;
  return children;
}
