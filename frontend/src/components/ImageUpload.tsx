import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { Upload, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

interface ImageUploadProps {
  productId: string;
  onSuccess?: () => void;
}

interface PreviewFile {
  file: File;
  preview: string;
  caption: string;
  imageType: string;
}

const IMAGE_TYPES = [
  { value: 'overview', label: 'Overview' },
  { value: 'pcb_front', label: 'PCB Front' },
  { value: 'pcb_back', label: 'PCB Back' },
  { value: 'closeup', label: 'Close-up' },
  { value: 'label', label: 'Label/FCC ID' },
  { value: 'internals', label: 'Internals' },
  { value: 'ports', label: 'Ports/Connectors' },
  { value: 'damage', label: 'Damage/Issue' },
  { value: 'other', label: 'Other' },
];

export default function ImageUpload({ productId, onSuccess }: ImageUploadProps) {
  const [files, setFiles] = useState<PreviewFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (previewFile: PreviewFile) => {
      const formData = new FormData();
      formData.append('image', previewFile.file);
      formData.append('image_type', previewFile.imageType);
      if (previewFile.caption) {
        formData.append('caption', previewFile.caption);
      }
      return products.uploadImage(productId, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    },
  });

  const handleFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;

    const validFiles = Array.from(newFiles).filter((file) => {
      // Check file type
      if (!file.type.startsWith('image/')) {
        return false;
      }
      // Check file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        return false;
      }
      return true;
    });

    const previews: PreviewFile[] = validFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      caption: '',
      imageType: 'overview',
    }));

    setFiles((prev) => [...prev, ...previews]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => {
      const newFiles = [...prev];
      URL.revokeObjectURL(newFiles[index].preview);
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const updateFile = (index: number, updates: Partial<PreviewFile>) => {
    setFiles((prev) => {
      const newFiles = [...prev];
      newFiles[index] = { ...newFiles[index], ...updates };
      return newFiles;
    });
  };

  const uploadAll = async () => {
    setUploadProgress(0);
    let completed = 0;

    for (const file of files) {
      try {
        await uploadMutation.mutateAsync(file);
        completed++;
        setUploadProgress(Math.round((completed / files.length) * 100));
      } catch (error) {
        console.error('Failed to upload:', file.file.name);
      }
    }

    // Clean up
    files.forEach((f) => URL.revokeObjectURL(f.preview));
    setFiles([]);
    setUploadProgress(null);
    onSuccess?.();
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={clsx(
          'border-2 border-dashed p-8 text-center cursor-pointer transition-all',
          isDragging
            ? 'border-cyber-cyan bg-cyber-cyan/10'
            : 'border-cyber-light/50 hover:border-cyber-cyan/50 hover:bg-cyber-dark/50'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
        />
        <Upload
          className={clsx(
            'h-10 w-10 mx-auto mb-3',
            isDragging ? 'text-cyber-cyan' : 'text-gray-500'
          )}
        />
        <p className="text-gray-400 mb-1">
          <span className="text-cyber-cyan">Click to upload</span> or drag and drop
        </p>
        <p className="text-xs text-gray-600 font-mono">
          PNG, JPG, GIF up to 10MB
        </p>
      </div>

      {/* Preview grid */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            {files.map((file, index) => (
              <div
                key={file.preview}
                className="card-cyber p-3 relative group"
              >
                {/* Remove button */}
                <button
                  onClick={() => removeFile(index)}
                  className="absolute top-2 right-2 p-1 bg-cyber-black/80 border border-cyber-pink/50 text-cyber-pink opacity-0 group-hover:opacity-100 transition-opacity z-10"
                >
                  <X className="h-4 w-4" />
                </button>

                {/* Preview image */}
                <div className="aspect-video bg-cyber-black mb-3 flex items-center justify-center overflow-hidden">
                  <img
                    src={file.preview}
                    alt="Preview"
                    className="max-w-full max-h-full object-contain"
                  />
                </div>

                {/* File info */}
                <div className="text-xs font-mono text-gray-500 mb-2 truncate">
                  {file.file.name} ({(file.file.size / 1024).toFixed(0)} KB)
                </div>

                {/* Image type select */}
                <select
                  value={file.imageType}
                  onChange={(e) => updateFile(index, { imageType: e.target.value })}
                  className="input-cyber text-sm py-1 mb-2"
                >
                  {IMAGE_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>

                {/* Caption input */}
                <input
                  type="text"
                  placeholder="Caption (optional)"
                  value={file.caption}
                  onChange={(e) => updateFile(index, { caption: e.target.value })}
                  className="input-cyber text-sm py-1"
                />
              </div>
            ))}
          </div>

          {/* Upload button */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500 font-mono">
              {files.length} image{files.length !== 1 ? 's' : ''} ready
            </div>
            <button
              onClick={uploadAll}
              disabled={uploadMutation.isPending || files.length === 0}
              className={clsx(
                'btn-cyber flex items-center gap-2',
                uploadMutation.isPending && 'opacity-50 cursor-not-allowed'
              )}
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  UPLOADING {uploadProgress}%
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  UPLOAD ALL
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Success message */}
      {uploadMutation.isSuccess && files.length === 0 && (
        <div className="flex items-center gap-2 p-3 border border-cyber-green/50 bg-cyber-green/10 text-cyber-green text-sm font-mono">
          <CheckCircle className="h-4 w-4" />
          Images uploaded successfully!
        </div>
      )}

      {/* Error message */}
      {uploadMutation.isError && (
        <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
          <AlertCircle className="h-4 w-4" />
          Failed to upload some images. Please try again.
        </div>
      )}
    </div>
  );
}
