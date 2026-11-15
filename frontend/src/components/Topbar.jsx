/**
 * Workspace header: breadcrumb, language, theme, real activity, and profile.
 * The activity list is the audit log for roles allowed to read it. Other
 * roles see an empty state rather than sample events.
 */
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, LogOut, Menu, UserRound } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import client, { unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { LanguageToggle } from './LanguageToggle';
import { ThemeToggle } from './ThemeToggle';
import { Avatar, IconButton } from './ui';
import { personName } from '../utils/format';

const PALETTES = ['evergreen', 'sapphire', 'indigo'];

export function Topbar({ title, onMenu }) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { palette, setPalette, setTheme } = useTheme();
  const [menu, setMenu] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [notes, setNotes] = useState(null);
  const wrap = useRef(null);

  useEffect(() => {
    const close = (event) => {
      if (wrap.current && !wrap.current.contains(event.target)) {
        setMenu(false);
        setNotesOpen(false);
      }
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const openNotes = async () => {
    setMenu(false);
    setNotesOpen((value) => !value);
    try {
      const response = await client.get('/notifications/');
      const notices = unwrap(response) || [];
      let audit = [];
      if (['super_admin', 'center_manager'].includes(user?.role)) {
        const auditResponse = await client.get('/reports/audit-logs/?page_size=5&ordering=-created_at');
        audit = unwrap(auditResponse).results || [];
      }
      setNotes([
        ...notices.map((note) => ({ id: `n-${note.id}`, message: note.title, created_at: note.created_at })),
        ...audit.map((note) => ({ id: `a-${note.id}`, message: note.message, created_at: note.created_at })),
      ]);
    } catch {
      setNotes([]);
    }
  };

  return (
    <header className="topbar" ref={wrap}>
      <IconButton className="menu-btn icon-btn" label={t('shell.menu')} onClick={onMenu}><Menu size={18} /></IconButton>
      <div className="breadcrumb">{t('shell.workspace')} <span>/</span> <span>{t(`roles.${user?.role}`)}</span> <span>/</span> <span>{title}</span></div>
      <div className="top-spacer" />
      <LanguageToggle />
      <ThemeToggle />
      <div className="menu-wrap">
        <IconButton label={t('shell.notifications')} onClick={openNotes}><Bell size={16} /></IconButton>
        {notesOpen ? (
          <div className="menu-panel" role="region" aria-label={t('shell.notifications')}>
            {(notes || []).length ? notes.map((note) => (
              <div key={note.id} className="activity-item">
                <div><strong>{note.message}</strong><small className="muted">{String(note.created_at).slice(0, 16).replace('T', ' ')}</small></div>
              </div>
            )) : <p className="muted" style={{ padding: 10 }}>{t('shell.emptyNotes')}</p>}
          </div>
        ) : null}
      </div>
      <div className="menu-wrap">
        <button type="button" className="top-person person" aria-expanded={menu} onClick={() => { setMenu((value) => !value); setNotesOpen(false); }}>
          <Avatar name={personName(user)} photo={user?.photo_url} size={36} />
          <span>
            <strong className="person-name">{personName(user)}</strong>
            <small>{t(`roles.${user?.role}`)}</small>
          </span>
        </button>
        {menu ? (
          <div className="menu-panel" role="menu">
            <Link to="/profile" onClick={() => setMenu(false)}><UserRound size={16} /> {t('nav.profile')}</Link>
            <button type="button" onClick={() => setPalette(PALETTES[(PALETTES.indexOf(palette) + 1) % PALETTES.length])}>
              {t(`palette.${palette}`)}
            </button>
            <button type="button" onClick={() => setTheme('system')}>{t('shell.system')}</button>
            <button type="button" onClick={logout}><LogOut size={16} /> {t('common.logout')}</button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
