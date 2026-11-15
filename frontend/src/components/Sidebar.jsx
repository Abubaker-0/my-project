/**
 * Primary navigation. On a narrow screen it is a drawer controlled by `open`.
 */
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import * as Icons from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { NAV } from '../nav';
import { Avatar } from './ui';
import { personName } from '../utils/format';

export function Sidebar({ open, onNavigate }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const items = NAV.filter((item) => item.roles.includes(user?.role));
  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand">
        <div className="brand-mark"><Icons.GraduationCap size={20} /></div>
        <div>
          <strong>{t('appName')}</strong>
          <span>{user?.center?.code || t(`roles.${user?.role}`)}</span>
        </div>
      </div>
      <nav className="nav-list">
        {items.map((item) => {
          const Icon = Icons[item.icon] || Icons.Circle;
          return (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} onClick={onNavigate}>
              <Icon size={18} />
              <span>{t(`nav.${item.key}`)}</span>
            </NavLink>
          );
        })}
      </nav>
      <NavLink to="/profile" className="sidebar-user" onClick={onNavigate}>
        <Avatar name={personName(user)} photo={user?.photo_url} />
        <div>
          <strong>{personName(user)}</strong>
          <small>{t(`roles.${user?.role}`)}</small>
        </div>
      </NavLink>
    </aside>
  );
}
