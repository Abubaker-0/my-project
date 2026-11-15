/**
 * The signed-in person's profile, photo, and password.
 * Photos are uploaded as multipart and shown through the authenticated photo URL.
 */
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import client, { errorMessage, unwrap } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Avatar, Button, Field, Input, ProfileCard, Select, TextArea } from '../components/ui';
import { personName } from '../utils/format';

export function ProfilePage() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const { toast } = useToast();
  const form = useForm({ defaultValues: user || {} });
  const password = useForm();
  if (!user) return null;
  return (
    <div className="grid split">
      <ProfileCard>
        <div className="person" style={{ marginBottom: 16 }}>
          <Avatar name={personName(user)} photo={user.photo_url} size={72} />
          <div>
            <h3>{personName(user)}</h3>
            <p className="muted">{t(`roles.${user.role}`)} · {user.center?.name || '—'}</p>
            <p className="muted">{user.email} · {user.phone}</p>
          </div>
        </div>
        <p className="muted">{t('common.profileHint')}</p>
        <form onSubmit={async (event) => {
          event.preventDefault();
          const file = event.currentTarget.photo.files[0];
          if (!file) return;
          const body = new FormData();
          body.append('photo', file);
          try {
            await client.post('/profile/photo/', body);
            const response = await client.get('/auth/me/');
            setUser(unwrap(response));
            toast(t('common.saved'), 'success');
          } catch (err) {
            toast(errorMessage(err), 'danger');
          }
        }}>
          <Field label={t('common.photo')}><Input name="photo" type="file" accept="image/jpeg,image/png,image/webp" /></Field>
          <Button type="submit">{t('common.upload')}</Button>
        </form>
      </ProfileCard>
      <div className="grid">
        <ProfileCard>
          <h3>{t('nav.profile')}</h3>
          <form className="form-grid" onSubmit={form.handleSubmit(async (values) => {
            try {
              const response = await client.patch('/profile/', {
                first_name: values.first_name,
                last_name: values.last_name,
                phone: values.phone,
                gender: values.gender,
                email: values.email,
                address: values.address || '',
                bio: values.bio || '',
                date_of_birth: values.date_of_birth || null,
              });
              setUser(unwrap(response));
              toast(t('common.saved'), 'success');
            } catch (err) {
              toast(errorMessage(err), 'danger');
            }
          })}>
            <Field label={t('common.firstName')}><Input {...form.register('first_name')} /></Field>
            <Field label={t('common.lastName')}><Input {...form.register('last_name')} /></Field>
            <Field label={t('common.email')}><Input {...form.register('email')} /></Field>
            <Field label={t('common.phone')}><Input {...form.register('phone')} /></Field>
            <Field label={t('common.gender')}>
              <Select {...form.register('gender')}>
                <option value="male">{t('common.male')}</option>
                <option value="female">{t('common.female')}</option>
              </Select>
            </Field>
            <Field label={t('common.birth')}><Input type="date" {...form.register('date_of_birth')} /></Field>
            <Field className="wide" label={t('common.address')}><Input {...form.register('address')} /></Field>
            <Field className="wide" label={t('common.bio')}><TextArea {...form.register('bio')} /></Field>
            <div className="row-actions wide"><Button type="submit">{t('common.save')}</Button></div>
          </form>
        </ProfileCard>
        <ProfileCard>
          <h3>{t('common.changePassword')}</h3>
          <p className="muted">{t('common.passwordHint')}</p>
          <form className="grid" onSubmit={password.handleSubmit(async (values) => {
            try {
              await client.post('/auth/change-password/', values);
              toast(t('common.saved'), 'success');
              password.reset();
            } catch (err) {
              toast(errorMessage(err), 'danger');
            }
          })}>
            <Field label={t('common.oldPassword')}><Input type="password" {...password.register('old_password', { required: true })} /></Field>
            <Field label={t('common.newPassword')}><Input type="password" {...password.register('new_password', { required: true })} /></Field>
            <Button type="submit">{t('common.save')}</Button>
          </form>
        </ProfileCard>
      </div>
    </div>
  );
}
