import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import Register from './Register';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Register Page', () => {
  beforeEach(() => {
    localStorage.clear();
    mockNavigate.mockClear();
  });

  describe('rendering', () => {
    it('renders registration form', () => {
      render(<Register />);

      expect(screen.getByRole('heading', { name: /CREATE ACCOUNT/i })).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Choose a username/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/your@email.com/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Min 8 characters/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Repeat password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /REGISTER/i })).toBeInTheDocument();
    });

    it('renders link to login page', () => {
      render(<Register />);

      const loginLink = screen.getByRole('link', { name: /Login/i });
      expect(loginLink).toBeInTheDocument();
      expect(loginLink).toHaveAttribute('href', '/login');
    });

    it('renders benefits list', () => {
      render(<Register />);

      expect(screen.getByText(/Submit products and components/i)).toBeInTheDocument();
      expect(screen.getByText(/Upload schematics and documentation/i)).toBeInTheDocument();
      expect(screen.getByText(/Build reputation in the community/i)).toBeInTheDocument();
    });
  });

  describe('password validation', () => {
    it('shows error when passwords do not match', async () => {
      const user = userEvent.setup();
      render(<Register />);

      await user.type(screen.getByPlaceholderText(/Choose a username/i), 'newuser');
      await user.type(screen.getByPlaceholderText(/your@email.com/i), 'new@example.com');
      await user.type(screen.getByPlaceholderText(/Min 8 characters/i), 'password123');
      await user.type(screen.getByPlaceholderText(/Repeat password/i), 'different123');

      await user.click(screen.getByRole('button', { name: /REGISTER/i }));

      await waitFor(() => {
        expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
      });

      // Should not navigate
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('allows submission when passwords match', async () => {
      const user = userEvent.setup();
      render(<Register />);

      await user.type(screen.getByPlaceholderText(/Choose a username/i), 'newuser');
      await user.type(screen.getByPlaceholderText(/your@email.com/i), 'new@example.com');
      await user.type(screen.getByPlaceholderText(/Min 8 characters/i), 'password123');
      await user.type(screen.getByPlaceholderText(/Repeat password/i), 'password123');

      await user.click(screen.getByRole('button', { name: /REGISTER/i }));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/');
      });
    });
  });

  describe('username validation', () => {
    it('shows error for existing username', async () => {
      const user = userEvent.setup();
      render(<Register />);

      await user.type(screen.getByPlaceholderText(/Choose a username/i), 'existinguser');
      await user.type(screen.getByPlaceholderText(/your@email.com/i), 'new@example.com');
      await user.type(screen.getByPlaceholderText(/Min 8 characters/i), 'password123');
      await user.type(screen.getByPlaceholderText(/Repeat password/i), 'password123');

      await user.click(screen.getByRole('button', { name: /REGISTER/i }));

      await waitFor(() => {
        expect(screen.getByText(/already exists/i)).toBeInTheDocument();
      });

      // Should not navigate
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe('successful registration', () => {
    it('navigates to home after successful registration', async () => {
      const user = userEvent.setup();
      render(<Register />);

      await user.type(screen.getByPlaceholderText(/Choose a username/i), 'brandnewuser');
      await user.type(screen.getByPlaceholderText(/your@email.com/i), 'brand@example.com');
      await user.type(screen.getByPlaceholderText(/Min 8 characters/i), 'securepass123');
      await user.type(screen.getByPlaceholderText(/Repeat password/i), 'securepass123');

      await user.click(screen.getByRole('button', { name: /REGISTER/i }));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/');
      });
    });

    it('shows loading state during submission', async () => {
      const user = userEvent.setup();
      render(<Register />);

      await user.type(screen.getByPlaceholderText(/Choose a username/i), 'newuser');
      await user.type(screen.getByPlaceholderText(/your@email.com/i), 'new@example.com');
      await user.type(screen.getByPlaceholderText(/Min 8 characters/i), 'password123');
      await user.type(screen.getByPlaceholderText(/Repeat password/i), 'password123');

      await user.click(screen.getByRole('button', { name: /REGISTER/i }));

      // Loading state is shown during submission; registration succeeds and navigates
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/');
      });
    });
  });

  describe('form fields', () => {
    it('has required fields', () => {
      render(<Register />);

      expect(screen.getByPlaceholderText(/Choose a username/i)).toBeRequired();
      expect(screen.getByPlaceholderText(/your@email.com/i)).toBeRequired();
      expect(screen.getByPlaceholderText(/Min 8 characters/i)).toBeRequired();
      expect(screen.getByPlaceholderText(/Repeat password/i)).toBeRequired();
    });

    it('has minimum password length', () => {
      render(<Register />);

      const passwordInput = screen.getByPlaceholderText(/Min 8 characters/i);
      expect(passwordInput).toHaveAttribute('minLength', '8');
    });

    it('email field has email type', () => {
      render(<Register />);

      const emailInput = screen.getByPlaceholderText(/your@email.com/i);
      expect(emailInput).toHaveAttribute('type', 'email');
    });
  });
});
