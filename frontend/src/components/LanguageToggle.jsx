/** Switches English and Dari and flips document direction. */
import { useTranslation } from 'react-i18next';
import { applyLanguage } from '../i18n';

export function LanguageToggle() {
  const { i18n, t } = useTranslation();
  const next = i18n.language === 'fa' ? 'en' : 'fa';
  return (
    <button
      type="button"
      className="ghost"
      onClick={() => {
        applyLanguage(next);
        i18n.changeLanguage(next);
      }}
    >
      {next === 'fa' ? t('common.dari') : t('common.english')}
    </button>
  );
}
