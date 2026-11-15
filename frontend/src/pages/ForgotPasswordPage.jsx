/**
 * Password recovery. DEBUG backends return a token so the flow can be finished
 * without an email server. The token is never stored by the client beyond the form.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { Button, Field, Input } from '../components/ui';

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [login, setLogin] = useState('');
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  return (
    <div className="login-form" style={{ minHeight: '100vh' }}>
      <div className="login-card card">
        <h2>{t('forgot.title')}</h2>
        <p className="muted">{t('forgot.subtitle')}</p>
        <form className="grid" style={{ marginTop: 16 }} onSubmit={async (event) => {
          event.preventDefault();
          setError('');
          try {
            const response = await client.post('/auth/forgot-password/', { login });
            const data = unwrap(response);
            setMessage(data.detail);
            if (data.debug_token) setToken(data.debug_token);
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <Field label={t('forgot.login')}><Input value={login} onChange={(event) => setLogin(event.target.value)} /></Field>
          <Button type="submit">{t('forgot.submit')}</Button>
        </form>
        <form className="grid" style={{ marginTop: 18 }} onSubmit={async (event) => {
          event.preventDefault();
          setError('');
          try {
            const response = await client.post('/auth/reset-password/', { token, new_password: password });
            setMessage(unwrap(response).detail);
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <Field label={t('forgot.token')}><Input value={token} onChange={(event) => setToken(event.target.value)} /></Field>
          <Field label={t('forgot.newPassword')}><Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></Field>
          <Button type="submit">{t('forgot.confirm')}</Button>
        </form>
        {message ? <p>{message}</p> : null}
        {error ? <p className="form-error">{error}</p> : null}
        <p style={{ marginTop: 12 }}><Link to="/login">{t('forgot.back')}</Link></p>
      </div>
    </div>
  );
}
