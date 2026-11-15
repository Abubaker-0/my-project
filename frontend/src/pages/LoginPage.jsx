/**
 * Sign-in screen. Demo buttons only fill the form; they do not bypass the API.
 */
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GraduationCap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { errorMessage } from '../api/client';
import { Button, Field, Input } from '../components/ui';
import { LanguageToggle } from '../components/LanguageToggle';
import { ThemeToggle } from '../components/ThemeToggle';

const DEMOS = [
  ['superadmin', 'Admin@12345', 'super_admin'],
  ['manager.kabul', 'Manager@12345', 'center_manager'],
  ['finance.kabul', 'Finance@12345', 'finance_manager'],
  ['teacher.zahra', 'Teacher@12345', 'teacher'],
  ['student.ali', 'Student@12345', 'student'],
];

export function LoginPage() {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const [error, setError] = useState('');
  const schema = useMemo(() => z.object({
    username: z.string().min(1, t('validation.required')),
    password: z.string().min(1, t('validation.required')),
  }), [t]);
  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm({ resolver: zodResolver(schema) });
  if (user) return <Navigate to="/" replace />;

  return (
    <div className="login-screen">
      <section className="login-panel">
        <div>
          <GraduationCap size={36} />
          <h2>{t('appName')}</h2>
          <p>{t('tagline')}</p>
        </div>
        <p>{t('login.subtitle')}</p>
      </section>
      <section className="login-form">
        <div className="login-card">
          <div className="row-actions" style={{ justifyContent: 'flex-end', marginBottom: 12 }}>
            <LanguageToggle />
            <ThemeToggle />
          </div>
          <h2 style={{ fontSize: 32, letterSpacing: '-0.04em' }}>{t('login.title')}</h2>
          <p className="muted" style={{ marginBottom: 16 }}>{t('login.subtitle')}</p>
          <form className="grid" onSubmit={handleSubmit(async (values) => {
            setError('');
            try {
              await login(values.username, values.password);
            } catch (err) {
              setError(errorMessage(err));
            }
          })}>
            <Field label={t('login.username')} error={errors.username?.message}>
              <Input autoComplete="username" {...register('username')} />
            </Field>
            <Field label={t('login.password')} error={errors.password?.message}>
              <Input type="password" autoComplete="current-password" {...register('password')} />
            </Field>
            {error ? <p className="form-error">{error}</p> : null}
            <Button type="submit" disabled={isSubmitting}>{t('login.submit')}</Button>
            <Link to="/forgot-password">{t('login.forgot')}</Link>
          </form>
          <div className="demo-list">
            <strong>{t('login.demo')}</strong>
            {DEMOS.map(([username, password, role]) => (
              <div className="demo-row" key={username}>
                <span>{t(`roles.${role}`)} · {username}</span>
                <Button variant="ghost" onClick={() => { setValue('username', username); setValue('password', password); }}>{t('login.fill')}</Button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
