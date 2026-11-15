/** Authenticated shell: sidebar, top bar, and the current page. */
import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { NAV } from '../nav';

export function Layout() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const match = NAV.find((item) => item.to !== '/' && pathname.startsWith(item.to));
  const title = pathname === '/' ? t('nav.dashboard') : t(`nav.${match?.key || 'dashboard'}`);
  return (
    <div className="app-shell">
      {open ? <div className="drawer-backdrop" onClick={() => setOpen(false)} /> : null}
      <Sidebar open={open} onNavigate={() => setOpen(false)} />
      <div className="main">
        <Topbar title={title} onMenu={() => setOpen(true)} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
