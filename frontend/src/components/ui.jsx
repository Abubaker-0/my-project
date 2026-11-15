/**
 * Shared controls: buttons, fields, dialogs, badges, and empty states.
 * They stay presentational. Pages own the API calls and validation.
 */
import { forwardRef, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Search, X } from 'lucide-react';
import client from '../api/client';

export function Button({ children, variant = 'primary', type = 'button', ...props }) {
  const className = variant === 'danger' ? 'danger-btn' : variant === 'ghost' ? 'ghost' : 'btn';
  return <button type={type} className={className} {...props}>{children}</button>;
}

export function IconButton({ children, label, ...props }) {
  return <button type="button" className="icon-btn" aria-label={label} {...props}>{children}</button>;
}

export function Field({ label, error, children, className = '' }) {
  return (
    <label className={`field ${className}`}>
      <span>{label}</span>
      {children}
      {error ? <small className="form-error">{error}</small> : null}
    </label>
  );
}

export const Input = forwardRef(function Input(props, ref) {
  return <input ref={ref} {...props} />;
});

export const Select = forwardRef(function Select({ children, ...props }, ref) {
  return <select ref={ref} {...props}>{children}</select>;
});

export const TextArea = forwardRef(function TextArea(props, ref) {
  return <textarea ref={ref} {...props} />;
});

export function SearchInput({ value, onChange, placeholder }) {
  return (
    <label className="field" style={{ minWidth: 220, flex: 1 }}>
      <span className="sr-only">{placeholder}</span>
      <span style={{ position: 'relative' }}>
        <Search size={16} style={{ position: 'absolute', insetInlineStart: 10, top: 12, color: 'var(--muted)' }} />
        <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} style={{ paddingInlineStart: 34 }} />
      </span>
    </label>
  );
}

export function FilterDropdown({ label, value, onChange, options }) {
  return (
    <label className="field" style={{ minWidth: 160 }}>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

export function DatePicker({ label, ...props }) {
  return <Field label={label}><input type="date" {...props} /></Field>;
}

export function TimePicker({ label, ...props }) {
  return <Field label={label}><input type="time" {...props} /></Field>;
}

const TONE = {
  active: 'success', inactive: 'warning', expired: 'warning', terminated: 'danger',
  pending: 'warning', approved: 'success', rejected: 'danger', paid: 'success',
  partially_paid: 'info', overdue: 'danger', refunded: 'info', issued: 'info',
  draft: 'warning', submitted_to_manager: 'info', sent_to_super_admin: 'success',
  present: 'success', absent: 'danger', cancelled: 'danger', dropped: 'warning',
};

export function Badge({ value, label }) {
  return <span className={`badge ${TONE[value] || ''}`}>{label || value}</span>;
}

export function Avatar({ name, photo, size = 36 }) {
  const [src, setSrc] = useState('');
  useEffect(() => {
    if (!photo) {
      setSrc('');
      return undefined;
    }
    let objectUrl = '';
    let cancelled = false;
    client.get(photo, { responseType: 'blob' })
      .then((response) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(response.data);
        setSrc(objectUrl);
      })
      .catch(() => setSrc(''));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photo]);
  const initials = (name || '?').split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  return (
    <span className="avatar" style={{ width: size, height: size, borderRadius: '50%', overflow: 'hidden', background: 'var(--primary-soft)', color: 'var(--primary)', display: 'grid', placeItems: 'center', fontSize: size < 32 ? 11 : 13, flex: '0 0 auto' }}>
      {src ? <img src={src} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : initials}
    </span>
  );
}

export function Modal({ title, open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <IconButton label="Close" onClick={onClose}><X size={18} /></IconButton>
        </div>
        <div style={{ marginTop: 14 }}>{children}</div>
      </div>
    </div>
  );
}

export function Drawer({ title, open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <IconButton label="Close" onClick={onClose}><X size={18} /></IconButton>
        </div>
        <div style={{ marginTop: 14 }}>{children}</div>
      </aside>
    </div>
  );
}

export function ConfirmDialog({ open, title, message, confirmLabel, cancelLabel, onConfirm, onClose, busy }) {
  return (
    <Modal title={title} open={open} onClose={onClose}>
      <p>{message}</p>
      <div className="row-actions" style={{ marginTop: 16 }}>
        <Button onClick={onConfirm} disabled={busy}>{confirmLabel}</Button>
        <Button variant="ghost" onClick={onClose}>{cancelLabel}</Button>
      </div>
    </Modal>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="row-actions" style={{ marginBottom: 14 }}>
      {tabs.map((tab) => (
        <button key={tab.value} type="button" className={tab.value === value ? 'btn' : 'ghost'} onClick={() => onChange(tab.value)}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function Pagination({ page, pageSize, count, onPage, labelPage, labelOf, labelRows }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  return (
    <div className="pager">
      <span>{count} {labelRows}</span>
      <div className="row-actions">
        <Button variant="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>‹</Button>
        <span>{labelPage} {page} {labelOf} {pages}</span>
        <Button variant="ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>›</Button>
      </div>
    </div>
  );
}

export function EmptyState({ title, text }) {
  return <div className="empty"><strong>{title}</strong><p>{text}</p></div>;
}

export function Loader({ label }) {
  return <div className="loader" role="status"><Loader2 className="spin" /><div>{label}</div></div>;
}

export function Card({ children, className = '' }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function StatCard({ label, value, icon }) {
  return (
    <article className="stat">
      <div className="icon">{icon}</div>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </article>
  );
}

export function ChartCard({ title, children }) {
  return <section className="chart-card"><h3>{title}</h3>{children}</section>;
}

export function ProfileCard({ children }) {
  return <section className="profile-card">{children}</section>;
}

export function Breadcrumbs({ items }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      {items.map((item, index) => (
        <span key={item.label}>
          {index > 0 ? ' / ' : ''}
          {item.to ? <Link to={item.to}>{item.label}</Link> : item.label}
        </span>
      ))}
    </nav>
  );
}
