/**
 * English (LTR) and Dari (RTL). The selected language is stored locally and
 * applied to the document direction so the whole layout flips.
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en/translation.json';
import fa from './locales/fa/translation.json';

const KEY = 'ctcms-lang';
const stored = localStorage.getItem(KEY) || 'en';

export function applyLanguage(code) {
  const language = code === 'fa' ? 'fa' : 'en';
  document.documentElement.lang = language === 'fa' ? 'fa' : 'en';
  document.documentElement.dir = language === 'fa' ? 'rtl' : 'ltr';
  localStorage.setItem(KEY, language);
  return language;
}

applyLanguage(stored);

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fa: { translation: fa },
  },
  lng: stored === 'fa' ? 'fa' : 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
