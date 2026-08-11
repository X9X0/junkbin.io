import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import ImageUpload from './ImageUpload';

describe('ImageUpload', () => {
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    mockOnSuccess.mockClear();
    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:test-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  describe('rendering', () => {
    it('renders upload dropzone', () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      expect(screen.getByText(/Click to upload/i)).toBeInTheDocument();
      expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
      expect(screen.getByText(/PNG, JPG, GIF up to 10MB/i)).toBeInTheDocument();
    });

    it('has hidden file input', () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]');
      expect(fileInput).toBeInTheDocument();
      expect(fileInput).toHaveClass('hidden');
    });

    it('accepts image files', () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]');
      expect(fileInput).toHaveAttribute('accept', 'image/*');
    });

    it('accepts multiple files', () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]');
      expect(fileInput).toHaveAttribute('multiple');
    });
  });

  describe('file validation', () => {
    it('accepts valid image files', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });

      // Use fireEvent for file input
      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByText(/1 image ready/i)).toBeInTheDocument();
      });
    });

    it('rejects non-image files', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const invalidFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      fireEvent.change(fileInput, { target: { files: [invalidFile] } });

      // Should not show as ready
      await waitFor(() => {
        expect(screen.queryByText(/image ready/i)).not.toBeInTheDocument();
      });
    });

    it('rejects files over 10MB', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

      // Create a mock large file
      const largeFile = new File([''], 'large.jpg', { type: 'image/jpeg' });
      Object.defineProperty(largeFile, 'size', { value: 15 * 1024 * 1024 }); // 15MB

      fireEvent.change(fileInput, { target: { files: [largeFile] } });

      // Should not show as ready
      await waitFor(() => {
        expect(screen.queryByText(/image ready/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('drag and drop', () => {
    it('shows drag state on dragover', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const dropzone = screen.getByText(/Click to upload/i).parentElement!;

      fireEvent.dragOver(dropzone);

      // Should have drag styling (border color change)
      await waitFor(() => {
        expect(dropzone.parentElement).toHaveClass('border-cyber-cyan');
      });
    });

    it('removes drag state on dragleave', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const dropzone = screen.getByText(/Click to upload/i).parentElement!;

      fireEvent.dragOver(dropzone);
      fireEvent.dragLeave(dropzone);

      // Should not have drag styling
      await waitFor(() => {
        expect(dropzone.parentElement).not.toHaveClass('border-cyber-cyan');
      });
    });

    it('handles file drop', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const dropzone = screen.getByText(/Click to upload/i).parentElement!.parentElement!;
      const validFile = new File(['test'], 'dropped.jpg', { type: 'image/jpeg' });

      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [validFile],
        },
      });

      await waitFor(() => {
        expect(screen.getByText(/1 image ready/i)).toBeInTheDocument();
      });
    });
  });

  describe('preview', () => {
    it('shows image preview after selection', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'preview.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByRole('img', { name: /Preview/i })).toBeInTheDocument();
      });
    });

    it('shows file name and size', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test content'], 'myimage.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByText(/myimage.jpg/i)).toBeInTheDocument();
      });
    });

    it('allows removing a file', async () => {
      const user = userEvent.setup();
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'remove.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByText(/1 image ready/i)).toBeInTheDocument();
      });

      // Find and click remove button - look for the card and its button
      const card = screen.getByText(/remove.jpg/i).closest('.card-cyber');
      const removeBtn = card?.querySelector('button');
      if (removeBtn) {
        await user.click(removeBtn);
      }

      // File should be removed - no longer showing ready count
      await waitFor(() => {
        expect(screen.queryByText(/image ready/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('image type selection', () => {
    it('shows image type selector', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'typed.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      // Should have image type options
      const select = screen.getByRole('combobox');
      expect(select).toHaveDisplayValue('Overview');
    });

    it('allows changing image type', async () => {
      const user = userEvent.setup();
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'typed.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'pcb_top');

      expect(select).toHaveDisplayValue('PCB Front');
    });
  });

  describe('upload', () => {
    it('shows upload all button when files are ready', async () => {
      render(<ImageUpload productId="test-product" onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'upload.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /UPLOAD ALL/i })).toBeInTheDocument();
      });
    });

    it('calls onSuccess after successful upload', async () => {
      const user = userEvent.setup();
      const mockUploadFn = vi.fn().mockResolvedValue({ id: 'img-1' });
      render(<ImageUpload uploadFn={mockUploadFn} onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'success.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /UPLOAD ALL/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /UPLOAD ALL/i }));

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('shows success message after upload', async () => {
      const user = userEvent.setup();
      const mockUploadFn = vi.fn().mockResolvedValue({ id: 'img-1' });
      render(<ImageUpload uploadFn={mockUploadFn} onSuccess={mockOnSuccess} />);

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const validFile = new File(['test'], 'success.jpg', { type: 'image/jpeg' });

      fireEvent.change(fileInput, { target: { files: [validFile] } });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /UPLOAD ALL/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /UPLOAD ALL/i }));

      await waitFor(() => {
        expect(screen.getByText(/images? uploaded/i)).toBeInTheDocument();
      });
    });
  });
});
