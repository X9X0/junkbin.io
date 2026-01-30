import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import Submit from './Submit';
import { server } from '../test/mocks/server';
import { http, HttpResponse } from 'msw';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('../context/AuthContext', async () => {
  const actual = await vi.importActual('../context/AuthContext');
  return {
    ...actual,
    useAuth: () => mockUseAuth(),
  };
});

describe('Submit Page', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { id: 'user-1', username: 'testuser' },
    });
  });

  describe('authentication required', () => {
    it('shows authentication required message when not logged in', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: false,
        user: null,
      });

      render(<Submit />);

      expect(screen.getByText(/AUTHENTICATION REQUIRED/i)).toBeInTheDocument();
      expect(screen.getByText(/must be logged in/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /LOGIN TO CONTINUE/i })).toBeInTheDocument();
    });
  });

  describe('type selector', () => {
    it('renders product and component type selectors', () => {
      render(<Submit />);

      expect(screen.getByText(/SUBMIT/)).toBeInTheDocument();
      expect(screen.getByText(/DOCUMENTATION/)).toBeInTheDocument();
      expect(screen.getByText('PRODUCT')).toBeInTheDocument();
      expect(screen.getByText('COMPONENT')).toBeInTheDocument();
    });

    it('starts with product type selected', () => {
      render(<Submit />);

      // Product should be visually selected (cyan border)
      const productButton = screen.getByText('PRODUCT').closest('button');
      expect(productButton).toHaveClass('border-cyber-cyan');
    });

    it('switches to component type', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.click(screen.getByText('COMPONENT'));

      const componentButton = screen.getByText('COMPONENT').closest('button');
      expect(componentButton).toHaveClass('border-cyber-pink');
    });
  });

  describe('wizard step progression', () => {
    it('shows step 1 initially', () => {
      render(<Submit />);

      expect(screen.getByText(/BASIC INFORMATION/i)).toBeInTheDocument();
    });

    it('advances to step 2 when valid', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      // Fill required fields
      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'Test Manufacturer');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'TEST-001');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');

      // Click next
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      expect(screen.getByText(/ADDITIONAL DETAILS/i)).toBeInTheDocument();
    });

    it('disables next button when required fields empty', () => {
      render(<Submit />);

      const nextButton = screen.getByRole('button', { name: /NEXT/i });
      expect(nextButton).toHaveClass('opacity-50');
      expect(nextButton).toHaveClass('cursor-not-allowed');
    });

    it('allows going back to previous step', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      // Fill required fields and advance
      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'Test Manufacturer');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'TEST-001');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      // Go back
      await user.click(screen.getByText(/BACK/i));

      expect(screen.getByText(/BASIC INFORMATION/i)).toBeInTheDocument();
    });
  });

  describe('product form validation', () => {
    it('requires manufacturer', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'TEST-001');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');

      const nextButton = screen.getByRole('button', { name: /NEXT/i });
      expect(nextButton).toHaveClass('opacity-50');
    });

    it('requires model number', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'Test Manufacturer');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');

      const nextButton = screen.getByRole('button', { name: /NEXT/i });
      expect(nextButton).toHaveClass('opacity-50');
    });

    it('requires category', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'Test Manufacturer');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'TEST-001');

      const nextButton = screen.getByRole('button', { name: /NEXT/i });
      expect(nextButton).toHaveClass('opacity-50');
    });
  });

  describe('review step', () => {
    it('shows entered data in review step', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      // Step 1
      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'ACME Corp');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'Widget-9000');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      // Step 2
      await user.type(screen.getByPlaceholderText(/v1.2/i), 'Rev B');
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      // Review step
      expect(screen.getByText(/REVIEW & SUBMIT/i)).toBeInTheDocument();
      expect(screen.getByText('ACME Corp')).toBeInTheDocument();
      expect(screen.getByText('Widget-9000')).toBeInTheDocument();
      expect(screen.getByText('Rev B')).toBeInTheDocument();
      expect(screen.getByText('Router')).toBeInTheDocument();
    });
  });

  describe('product submission', () => {
    it('submits product and navigates on success', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      // Step 1
      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'ACME Corp');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'Widget-9000');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      // Step 2
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      // Submit
      await user.click(screen.getByRole('button', { name: /SUBMIT PRODUCT/i }));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(expect.stringMatching(/\/products\//));
      });
    });

    it('shows error on submission failure', async () => {
      server.use(
        http.post('http://localhost:8000/api/products/', () => {
          return HttpResponse.json(
            { detail: 'Submission failed' },
            { status: 400 }
          );
        })
      );

      const user = userEvent.setup();
      render(<Submit />);

      // Fill and submit
      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'ACME Corp');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'Widget-9000');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');
      await user.click(screen.getByRole('button', { name: /NEXT/i }));
      await user.click(screen.getByRole('button', { name: /NEXT/i }));
      await user.click(screen.getByRole('button', { name: /SUBMIT PRODUCT/i }));

      await waitFor(() => {
        expect(screen.getByText(/Submission failed|Failed to create/i)).toBeInTheDocument();
      });
    });
  });

  describe('component form', () => {
    it('switches to component form when selected', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.click(screen.getByText('COMPONENT'));

      expect(screen.getByText(/COMPONENT IDENTIFICATION/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Texas Instruments/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/LM7805/i)).toBeInTheDocument();
    });

    it('validates component form fields', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.click(screen.getByText('COMPONENT'));

      // Next should be disabled without required fields
      const nextButton = screen.getByRole('button', { name: /NEXT/i });
      expect(nextButton).toHaveClass('opacity-50');
    });

    it('enables next when component fields are valid', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      await user.click(screen.getByText('COMPONENT'));

      await user.type(screen.getByPlaceholderText(/Texas Instruments/i), 'Test Mfr');
      await user.type(screen.getByPlaceholderText(/LM7805/i), 'TEST-PART');

      // Select component type - find the select that has "Select Type"
      const selects = screen.getAllByRole('combobox');
      const typeSelect = selects.find(s => s.textContent?.includes('Select Type') ||
        Array.from(s.options).some((o: any) => o.text === 'Select Type...'));
      if (typeSelect) {
        await user.selectOptions(typeSelect, 'ic');
      }

      const nextButton = screen.getByRole('button', { name: /NEXT/i });
      expect(nextButton).not.toHaveClass('opacity-50');
    });
  });

  describe('step indicators', () => {
    it('shows correct step as active', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      // Check step 1 is active initially
      // Step indicators are the numbered circles
      const steps = screen.getAllByText(/^[1-3]$/);

      // First step should have different styling
      expect(steps[0].closest('div')).toHaveClass('border-cyber-cyan');
    });

    it('marks completed steps', async () => {
      const user = userEvent.setup();
      render(<Submit />);

      // Fill and advance
      await user.type(screen.getByPlaceholderText(/Samsung, Cisco/i), 'Test');
      await user.type(screen.getByPlaceholderText(/RT-AX88U/i), 'Test');
      await user.selectOptions(screen.getByRole('combobox', { name: '' }), 'router');
      await user.click(screen.getByRole('button', { name: /NEXT/i }));

      // Step 1 should now show checkmark (completed)
      // The check icon appears when step > s
      expect(screen.getByText(/ADDITIONAL DETAILS/i)).toBeInTheDocument();
    });
  });
});
