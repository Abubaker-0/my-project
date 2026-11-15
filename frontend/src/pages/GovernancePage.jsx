/**
 * Super admin inspection of the permission ceiling, restrictions, and integrity findings.
 * Protected duties cannot be turned off from this screen.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useToast } from '../context/ToastContext';
import { Button, Card } from '../components/ui';

export function GovernancePage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [catalog, setCatalog] = useState([]);
  const [issues, setIssues] = useState(null);

  useEffect(() => {
    client.get('/permissions/catalog/').then((response) => setCatalog(unwrap(response))).catch((err) => toast(errorMessage(err), 'danger'));
    client.get('/reports/integrity/').then((response) => setIssues(unwrap(response).issues || [])).catch((err) => toast(errorMessage(err), 'danger'));
  }, []);

  const restrictExport = async () => {
    try {
      await client.post('/permissions/overrides/', { role: 'finance_manager', code: 'exports.invoices', allowed: false });
      toast(t('common.saved'), 'success');
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
        {issues && !issues.length ? <p>{t('common.noIssues')}</p> : null}
        {(issues || []).map((issue, index) => <p key={index}>{issue.code} {issue.invoice || issue.center || ''}</p>)}
      </Card>
      <Card>
        <h3>{t('common.permissions')}</h3>
        <p className="muted">{t('common.permissionHint')}</p>
        {catalog.map((item) => (
          <p key={item.code}><strong>{item.code}</strong> — {item.description} {item.protected ? `(${t('common.protected')})` : ''}</p>
        ))}
        <Button onClick={restrictExport}>{t('common.restrictExports')}</Button>
      </Card>
    </div>
  );
}
