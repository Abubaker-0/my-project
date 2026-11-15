/**
 * The sign-in screen is shared. It must not ask the visitor to pick a role.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { LoginPage } from '../pages/LoginPage';
import '../i18n';

function renderLogin() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe('unified login', () => {
  it('shows one welcome form and no role selector', () => {
    renderLogin();
    expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/toggle decorative lamp/i)).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /role/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in securely/i })).toBeEnabled();
  });
});
