/**
 * One sign-in screen for every role. The API decides the dashboard.
 * The lamp is decorative: the form stays usable when it is off and when
 * motion is reduced.
 */
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowUpRight, Eye, EyeOff, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { errorMessage } from '../api/client';
import { Button, Input } from '../components/ui';
import { LanguageToggle } from '../components/LanguageToggle';
import { ThemeToggle } from '../components/ThemeToggle';

const REMEMBER = 'ctcms-remember-login';
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
  const [showPassword, setShowPassword] = useState(false);
  const [lampOn, setLampOn] = useState(false);
  const remembered = localStorage.getItem(REMEMBER) || '';
  const schema = useMemo(() => z.object({
    username: z.string().min(1, t('validation.required')),
    password: z.string().min(1, t('validation.required')),
    remember: z.boolean().optional(),
  }), [t]);
  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { username: remembered, remember: Boolean(remembered), password: '' },
  });
  if (user) return <Navigate to="/" replace />;

  return (
    <div className="login-screen">
      <section className="login-panel">
        <div className="hero-brand">
          <span className="small-mark"><Sparkles size={18} /></span>
          <span>{t('appName')}</span>
          <small style={{ fontWeight: 450, opacity: 0.75 }}>/ {t('brandSub')}</small>
        </div>
        <div className={`lamp${lampOn ? ' on' : ''}`}>
          <div className="lamp-stem" />
          <div className="lamp-shade" />
          <div className="lamp-bulb" />
          <div className="lamp-glow" />
          <button
            type="button"
            className="lamp-cord"
            aria-pressed={lampOn}
            aria-label={t('login.lamp')}
            onClick={() => setLampOn((value) => !value)}
          />
        </div>
        <div className="hero-copy">
          <span className="hero-pill"><span className="hero-dot" /> {t('login.pill')}</span>
          <h1>{t('login.heroTitle')}</h1>
          <p>{t('login.heroText')}</p>
        </div>
        <div className="hero-foot"><i /> {t('login.footer')}</div>
      </section>
      <section className="login-form">
        <div className="login-utilities">
          <span>{t('login.secure')}</span>
          <LanguageToggle />
          <ThemeToggle />
        </div>
        <div className="login-card">
          <div className="eyebrow">{t('login.kicker')}</div>
          <h2>{t('login.welcome')}</h2>
          <p className="subtitle">{t('login.lead')}</p>
          <form className="grid" onSubmit={handleSubmit(async (values) => {
            setError('');
            if (values.remember) localStorage.setItem(REMEMBER, values.username);
            else localStorage.removeItem(REMEMBER);
            try {
              await login(values.username, values.password);
            } catch (err) {
              setError(errorMessage(err));
            }
          })}>
            <label className="field">
              {t('login.username')}
              <Input autoComplete="username" placeholder={t('login.usernamePlaceholder')} {...register('username')} />
              {errors.username ? <small className="form-error">{errors.username.message}</small> : null}
            </label>
            <label className="field">
              {t('login.password')}
              <span className="password-wrap">
                <Input type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder={t('login.passwordPlaceholder')} {...register('password')} />
                <button type="button" className="password-toggle" aria-label={showPassword ? t('login.hide') : t('login.show')} onClick={() => setShowPassword((value) => !value)}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
              {errors.password ? <small className="form-error">{errors.password.message}</small> : null}
            </label>
            <div className="form-help">
              <label className="check"><input type="checkbox" {...register('remember')} /> {t('login.remember')}</label>
              <Link to="/forgot-password">{t('login.forgot')}</Link>
            </div>
            {error ? <p className="form-error" role="alert">{error}</p> : null}
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? t('common.loading') : t('login.submit')} <ArrowUpRight size={16} /></Button>
          </form>
          <p className="safety-note">{t('login.note')}</p>
          <details className="demo-list">
            <summary>{t('login.demo')}</summary>
            {DEMOS.map(([username, password, role]) => (
              <div className="demo-row" key={username}>
                <span>{t(`roles.${role}`)} · {username}</span>
                <Button variant="ghost" onClick={() => { setValue('username', username, { shouldDirty: true }); setValue('password', password, { shouldDirty: true }); }}>{t('login.fill')}</Button>
              </div>
            ))}
          </details>
        </div>
      </section>
    </div>
  );
}
