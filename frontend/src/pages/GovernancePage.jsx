/**
 * Bounded permission administration. Protected duties are visible and locked.
 * A change is previewed, then stored with a reason, and can be restored.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useToast } from '../context/ToastContext';
import { Button, Card, Field, Input } from '../components/ui';

export function GovernancePage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [matrix, setMatrix] = useState(null);
  const [history, setHistory] = useState([]);
  const [issues, setIssues] = useState([]);
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState(null);

  const load = () => {
    client.get('/permissions/matrix/').then((response) => setMatrix(unwrap(response))).catch((err) => toast(errorMessage(err), 'danger'));
    client.get('/permissions/history/').then((response) => setHistory(unwrap(response) || [])).catch(() => setHistory([]));
    client.get('/reports/integrity/').then((response) => setIssues(unwrap(response).issues || [])).catch(() => setIssues([]));
  };
  useEffect(load, []);

  const propose = async (role, code, allowed) => {
    try {
      const response = await client.post('/permissions/preview/', { role, code, allowed, reason });
      setPreview(unwrap(response));
    } catch (err) {
      toast(errorMessage(err), 'danger');
    }
  };
  const apply = async (role, code, allowed) => {
    try {
      await client.post('/permissions/overrides/', { role, code, allowed, reason });
      setPreview(null);
      toast(t('common.saved'), 'success');
      load();
    } catch (err) {
      toast(errorMessage(err), 'danger');
    }
  };
  const restore = async (version) => {
    try {
      await client.post('/permissions/restore/', { version, reason });
      toast(t('common.saved'), 'success');
      load();
    } catch (err) {
      toast(errorMessage(err), 'danger');
    }
  };

  return (
    <div className="grid">
      <div className="page-head"><h2>{t('nav.governance')}</h2></div>
      <Card>
        <h3>{t('common.integrity')}</h3>
        <p className="muted">{t('common.integrityHint')}</p>
        {!issues.length ? <p>{t('common.noIssues')}</p> : issues.map((issue) => (
          <p key={`${issue.code}-${issue.invoice || issue.enrollment || issue.center || ''}`}>{issue.code}</p>
        ))}
      </Card>
      <Card>
        <h3>{t('common.permissions')}</h3>
        <p className="muted">{t('common.permissionHint')}</p>
        <p className="muted">{matrix?.lockout}</p>
        <Field label={t('common.reason')}><Input value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
        {preview ? (
          <p>
            {preview.code}: {String(preview.current_allowed)} → {String(preview.proposed_allowed)}. {preview.effect}
            {(preview.closes || []).join(', ')}
          </p>
        ) : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t('common.permissions')}</th>
                {(matrix?.roles || []).map((role) => <th key={role}>{t(`roles.${role}`)}</th>)}
              </tr>
            </thead>
            <tbody>
              {(matrix?.rows || []).map((row) => (
                <tr key={row.code}>
                  <td>
                    <strong>{row.code}</strong>
                    <div className="muted">{row.protected ? t('common.protected') : t('common.configurable')}</div>
                    <div className="muted">{row.scope}. {row.conditions}</div>
                  </td>
                  {(matrix?.roles || []).map((role) => {
                    const cell = row.cells[role];
                    return (
                      <td key={role}>
                        <div>{cell.source}</div>
                        {cell.configurable ? (
                          <div className="row-actions">
                            <Button variant="ghost" onClick={() => propose(role, row.code, !cell.allowed)}>{t('common.preview')}</Button>
                            <Button onClick={() => apply(role, row.code, !cell.allowed)}>{cell.allowed ? t('common.restrict') : t('common.restore')}</Button>
                          </div>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card>
        <h3>{t('common.history')}</h3>
        {history.map((row) => (
          <div className="row-actions" key={row.version}>
            <span>v{row.version} {row.code} {row.role} — {row.reason}</span>
            <Button variant="ghost" onClick={() => restore(row.version)}>{t('common.restore')}</Button>
          </div>
        ))}
      </Card>
    </div>
  );
}
