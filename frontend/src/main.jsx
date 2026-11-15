/**
 * Application entry. Theme and language are applied before the first screen
 * so Dari and dark mode do not flash the wrong direction or palette.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/vazirmatn/400.css';
import '@fontsource/vazirmatn/600.css';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ToastViewport } from './components/Toast';
import './i18n';
import './styles/global.css';

const storedTheme = localStorage.getItem('ctcms-theme') || 'light';
document.documentElement.dataset.theme = storedTheme;

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <App />
            <ToastViewport />
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
