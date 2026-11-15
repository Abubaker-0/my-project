/** Switches light and dark and keeps the choice in localStorage. */
import { Moon, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../context/ThemeContext';
import { IconButton } from './ui';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useTranslation();
  const dark = theme === 'dark';
  return (
    <IconButton label={dark ? t('common.light') : t('common.dark')} onClick={toggleTheme}>
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </IconButton>
  );
}
