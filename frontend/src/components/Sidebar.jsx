/**
 * Dark academic sidebar. Links are grouped and limited to the signed-in role.
 * Collapsing hides labels on desktop; the mobile drawer always shows them.
 */
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import * as Icons from 'lucide-react';
import { PanelLeft } from 'lucide-react';
import { NAV, NAV_GROUPS } from '../nav';
import { useAuth } from '../context/AuthContext';

export function Sidebar({ open, collapsed, onToggleCollapse, onNavigate }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const allowed = NAV.filter((item) => item.roles.includes(user?.role));
  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand">
        <div className="brand-mark"><Icons.Sparkles size={16} /></div>
        <div className="brand-copy">
          <strong>{t('appName')}</strong>
          <span>{t('brandSub')}</span>
        </div>
        <button type="button" className="collapse-btn" aria-label={t('shell.collapse')} onClick={onToggleCollapse}>
          <PanelLeft size={16} />
        </button>
      </div>
      <nav className="nav-list" aria-label={t('shell.menu')}>
        {NAV_GROUPS.map((group) => {
          const items = allowed.filter((item) => group.keys.includes(item.key));
          if (!items.length) return null;
          return (
            <div className="nav-group" key={group.id}>
              <div className="side-caption">{t(group.label)}</div>
              {items.map((item) => {
                const Icon = Icons[item.icon] || Icons.Circle;
                return (
                  <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} onClick={onNavigate}>
                    <Icon size={18} />
                    <span className="nav-label">{t(`nav.${item.key}`)}</span>
                  </NavLink>
                );
              })}
            </div>
          );
        })}
      </nav>
      <div className="sidebar-foot"><span>{t('shell.foot')}</span></div>
    </aside>
  );
}
