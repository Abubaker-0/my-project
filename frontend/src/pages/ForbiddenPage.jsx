/** Shown when a signed-in role opens a route reserved for someone else. */
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function ForbiddenPage() {
  const { t } = useTranslation();
  return (
    <div className="empty">
      <h2>{t('common.forbidden')}</h2>
      <Link to="/">{t('common.back')}</Link>
    </div>
  );
}
