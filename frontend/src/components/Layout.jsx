/** Authenticated shell shared by every role. */
import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { pageKey } from '../nav';

const COLLAPSE = 'ctcms-sidebar';

export function Layout() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE) === '1');
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const title = t(`nav.${pageKey(pathname)}`);
  return (
    <div className={`app-shell${collapsed ? ' collapsed' : ''}`}>
      {open ? <div className="drawer-backdrop" onClick={() => setOpen(false)} /> : null}
      <Sidebar
        open={open}
        collapsed={collapsed}
        onNavigate={() => setOpen(false)}
        onToggleCollapse={() => setCollapsed((value) => {
          localStorage.setItem(COLLAPSE, value ? '0' : '1');
          return !value;
        })}
      />
      <div className="main">
        <Topbar title={title} onMenu={() => setOpen((value) => !value)} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
