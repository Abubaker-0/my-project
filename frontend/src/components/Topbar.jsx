/** Top bar with the page title, language, theme, and sign out. */
import { LogOut, Menu } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { LanguageToggle } from './LanguageToggle';
import { ThemeToggle } from './ThemeToggle';
import { IconButton } from './ui';
import { personName } from '../utils/format';
import { Avatar } from './ui';
import { Link } from 'react-router-dom';

export function Topbar({ title, onMenu }) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  return (
    <header className="topbar">
      <IconButton className="menu-btn icon-btn" label="Menu" onClick={onMenu}><Menu size={18} /></IconButton>
      <h1>{title}</h1>
      <div className="top-spacer" />
      <LanguageToggle />
      <ThemeToggle />
      <Link to="/profile" aria-label={t('nav.profile')}><Avatar name={personName(user)} photo={user?.photo_url} size={36} /></Link>
      <IconButton label={t('common.logout')} onClick={logout}><LogOut size={18} /></IconButton>
    </header>
  );
}
