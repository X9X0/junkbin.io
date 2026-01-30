import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import AddComponentForm from './AddComponentForm';
import { mockComponent } from '../test/mocks/handlers';

describe('AddComponentForm', () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    mockOnSuccess.mockClear();
    mockOnCancel.mockClear();
  });

  describe('mode switching', () => {
    it('renders with search mode by default', () => {
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText(/SEARCH EXISTING/i)).toBeInTheDocument();
      expect(screen.getByText(/ADD NEW/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Search by part number/i)).toBeInTheDocument();
    });

    it('switches to new component mode', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      await user.click(screen.getByText(/ADD NEW/i));

      expect(screen.getByPlaceholderText(/e.g., LM7805/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e.g., Texas Instruments/i)).toBeInTheDocument();
      expect(screen.getByText(/Select type.../i)).toBeInTheDocument();
    });

    it('switches back to search mode', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      // Switch to new mode
      await user.click(screen.getByText(/ADD NEW/i));

      // Switch back to search mode
      await user.click(screen.getByText(/SEARCH EXISTING/i));

      expect(screen.getByPlaceholderText(/Search by part number/i)).toBeInTheDocument();
    });
  });

  describe('search mode', () => {
    it('shows search results when typing', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const searchInput = screen.getByPlaceholderText(/Search by part number/i);
      await user.type(searchInput, 'TEST');

      await waitFor(() => {
        expect(screen.getByText(mockComponent.part_number)).toBeInTheDocument();
      });
    });

    it('shows no results message for non-matching search', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const searchInput = screen.getByPlaceholderText(/Search by part number/i);
      await user.type(searchInput, 'notfound');

      await waitFor(() => {
        expect(screen.getByText(/No components found/i)).toBeInTheDocument();
      });
    });

    it('allows selecting a component', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const searchInput = screen.getByPlaceholderText(/Search by part number/i);
      await user.type(searchInput, 'TEST');

      await waitFor(() => {
        expect(screen.getByText(mockComponent.part_number)).toBeInTheDocument();
      });

      // Click on the result
      await user.click(screen.getByText(mockComponent.part_number));

      // Selected component should be highlighted
      const selectedPreview = screen.getAllByText(mockComponent.part_number);
      expect(selectedPreview.length).toBeGreaterThan(0);
    });
  });

  describe('new component mode', () => {
    it('validates required fields', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      // Switch to new mode
      await user.click(screen.getByText(/ADD NEW/i));

      // Submit button should be disabled without required fields
      const submitButton = screen.getByRole('button', { name: /ADD COMPONENT/i });
      expect(submitButton).toBeDisabled();
    });

    it('enables submit when required fields are filled', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      // Switch to new mode
      await user.click(screen.getByText(/ADD NEW/i));

      // Fill required fields
      await user.type(screen.getByPlaceholderText(/e.g., LM7805/i), 'NEW-PART');
      await user.type(screen.getByPlaceholderText(/e.g., Texas Instruments/i), 'New Mfr');

      // Select component type
      const typeSelect = screen.getByRole('combobox');
      await user.selectOptions(typeSelect, 'ic');

      // Submit button should be enabled
      const submitButton = screen.getByRole('button', { name: /ADD COMPONENT/i });
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('location fields', () => {
    it('shows location fields in both modes', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByPlaceholderText(/e.g., U1, R5/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e.g., Near HDMI port/i)).toBeInTheDocument();

      // Also visible in new mode
      await user.click(screen.getByText(/ADD NEW/i));

      expect(screen.getByPlaceholderText(/e.g., U1, R5/i)).toBeInTheDocument();
    });

    it('allows setting quantity', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      const quantityInput = screen.getByRole('spinbutton');
      await user.clear(quantityInput);
      await user.type(quantityInput, '5');

      expect(quantityInput).toHaveValue(5);
    });
  });

  describe('submission', () => {
    it('calls onSuccess after successful submission', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      // Search and select a component
      const searchInput = screen.getByPlaceholderText(/Search by part number/i);
      await user.type(searchInput, 'TEST');

      await waitFor(() => {
        expect(screen.getByText(mockComponent.part_number)).toBeInTheDocument();
      });

      await user.click(screen.getByText(mockComponent.part_number));

      // Submit
      const submitButton = screen.getByRole('button', { name: /ADD COMPONENT/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('shows success message after submission', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      // Search and select a component
      const searchInput = screen.getByPlaceholderText(/Search by part number/i);
      await user.type(searchInput, 'TEST');

      await waitFor(() => {
        expect(screen.getByText(mockComponent.part_number)).toBeInTheDocument();
      });

      await user.click(screen.getByText(mockComponent.part_number));

      // Submit
      const submitButton = screen.getByRole('button', { name: /ADD COMPONENT/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/added successfully/i)).toBeInTheDocument();
      });
    });
  });

  describe('cancel', () => {
    it('calls onCancel when cancel button clicked', async () => {
      const user = userEvent.setup();
      render(
        <AddComponentForm
          productId="test-product"
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      );

      await user.click(screen.getByText(/CANCEL/i));

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });
});
