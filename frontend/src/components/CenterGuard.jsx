/**
 * Operational pages require a center. Super admin is exempt because they
 * review every center and do not belong to one.
 */
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { EmptyState } from './ui';

export function CenterGuard({ children }) {
  const { user } = useAuth();
  const { t } = useTranslation();
  if (user?.role !== 'super_admin' && !user?.center) {
    return <EmptyState title={t('common.noCenter')} text="" />;
  }
  return children;
}
