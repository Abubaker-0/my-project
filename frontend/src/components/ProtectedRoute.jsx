/** Sends anonymous visitors to the login page. */
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader } from './ui';
import { useTranslation } from 'react-i18next';

export function ProtectedRoute({ children }) {
  const { user, ready } = useAuth();
  const { t } = useTranslation();
  const location = useLocation();
  if (!ready) return <Loader label={t('common.loading')} />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}
