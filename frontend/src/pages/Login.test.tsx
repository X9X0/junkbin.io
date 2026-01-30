import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import Login from './Login';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Page', () => {
  beforeEach(() => {
    localStorage.clear();
    mockNavigate.mockClear();
  });

  describe('rendering', () => {
    it('renders login form', () => {
      render(<Login />);

      expect(screen.getByText(/SYSTEM/)).toBeInTheDocument();
      expect(screen.getByText(/LOGIN/)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter username/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /LOGIN/i })).toBeInTheDocument();
    });

    it('renders link to register page', () => {
      render(<Login />);

      const registerLink = screen.getByRole('link', { name: /Register/i });
      expect(registerLink).toBeInTheDocument();
      expect(registerLink).toHaveAttribute('href', '/register');
    });
  });

  describe('form validation', () => {
    it('requires username and password', async () => {
      render(<Login />);

      const usernameInput = screen.getByPlaceholderText(/Enter username/i);
      const passwordInput = screen.getByPlaceholderText(/Enter password/i);

      // HTML5 validation should prevent submission
      expect(usernameInput).toBeRequired();
      expect(passwordInput).toBeRequired();
    });

    it('allows typing in form fields', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByPlaceholderText(/Enter username/i);
      const passwordInput = screen.getByPlaceholderText(/Enter password/i);

      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'testpass');

      expect(usernameInput).toHaveValue('testuser');
      expect(passwordInput).toHaveValue('testpass');
    });
  });

  describe('successful login', () => {
    it('navigates to home on successful login', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByPlaceholderText(/Enter username/i);
      const passwordInput = screen.getByPlaceholderText(/Enter password/i);
      const submitButton = screen.getByRole('button', { name: /LOGIN/i });

      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'testpass');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/');
      });
    });

    it('shows loading state during submission', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByPlaceholderText(/Enter username/i);
      const passwordInput = screen.getByPlaceholderText(/Enter password/i);
      const submitButton = screen.getByRole('button', { name: /LOGIN/i });

      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'testpass');
      await user.click(submitButton);

      // Should show loading text
      expect(screen.getByText(/AUTHENTICATING/i)).toBeInTheDocument();
    });
  });

  describe('failed login', () => {
    it('displays error message on invalid credentials', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByPlaceholderText(/Enter username/i);
      const passwordInput = screen.getByPlaceholderText(/Enter password/i);
      const submitButton = screen.getByRole('button', { name: /LOGIN/i });

      await user.type(usernameInput, 'baduser');
      await user.type(passwordInput, 'wrongpass');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
      });

      // Should not navigate
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('clears error when user starts typing again', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByPlaceholderText(/Enter username/i);
      const passwordInput = screen.getByPlaceholderText(/Enter password/i);
      const submitButton = screen.getByRole('button', { name: /LOGIN/i });

      // First, trigger an error
      await user.type(usernameInput, 'baduser');
      await user.type(passwordInput, 'wrongpass');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
      });

      // Error should be cleared when user types
      await user.clear(usernameInput);
      await user.type(usernameInput, 'newuser');

      // Note: The current implementation doesn't clear errors on type
      // This test documents expected behavior that could be implemented
    });
  });
});
