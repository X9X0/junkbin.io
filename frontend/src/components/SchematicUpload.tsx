import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { Upload, X, Loader2, CheckCircle, AlertCircle, FileText, Clock, TrendingUp } from 'lucide-react';
import clsx from 'clsx';

interface SchematicUploadProps {
  productId: string;
  onSuccess?: () => void;
}

interface PreviewFile {
  file: File;
  title: string;
  description: string;
  schematicType: string;
  sourceType: string;
  sourceUrl: string;
  version: string;
  pageCount: string;
}

const SCHEMATIC_TYPES = [
  { value: 'full_schematic', label: 'Full Schematic' },
  { value: 'block_diagram', label: 'Block Diagram' },
  { value: 'pcb_layout', label: 'PCB Layout' },
  { value: 'service_manual', label: 'Service Manual' },
  { value: 'datasheet', label: 'Component Datasheet' },
  { value: 'pinout', label: 'Pinout Diagram' },
  { value: 'wiring_diagram', label: 'Wiring Diagram' },
  { value: 'bom', label: 'Bill of Materials' },
  { value: 'other', label: 'Other Documentation' },
];

const SOURCE_TYPES = [
  { value: 'community', label: 'Community Contributed' },
  { value: 'official', label: 'Official/Manufacturer' },
  { value: 'reverse_engineered', label: 'Reverse Engineered' },
  { value: 'fcc_filing', label: 'FCC Filing' },
  { value: 'leaked', label: 'Leaked Document' },
  { value: 'unknown', label: 'Unknown Source' },
];

const ALLOWED_TYPES = [
  'application/pdf',
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
  'application/zip',
  'application/x-zip-compressed',
];

const ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'zip'];

export default function SchematicUpload({ productId, onSuccess }: SchematicUploadProps) {
  const [file, setFile] = useState<PreviewFile | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (previewFile: PreviewFile) => {
      const formData = new FormData();
      formData.append('file', previewFile.file);
      formData.append('title', previewFile.title);
      formData.append('schematic_type', previewFile.schematicType);
      formData.append('source_type', previewFile.sourceType);
      if (previewFile.description) {
        formData.append('description', previewFile.description);
      }
      if (previewFile.sourceUrl) {
        formData.append('source_url', previewFile.sourceUrl);
      }
      if (previewFile.version) {
        formData.append('version', previewFile.version);
      }
      if (previewFile.pageCount) {
        formData.append('page_count', previewFile.pageCount);
      }
      return products.uploadSchematic(productId, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'schematics'] });
      setFile(null);
      onSuccess?.();
    },
  });

  const handleFile = (newFile: File | null) => {
    if (!newFile) return;

    // Check file type
    const ext = newFile.name.split('.').pop()?.toLowerCase() || '';
    if (!ALLOWED_TYPES.includes(newFile.type) && !ALLOWED_EXTENSIONS.includes(ext)) {
      return;
    }

    // Check file size (max 50MB for schematics)
    if (newFile.size > 50 * 1024 * 1024) {
      return;
    }

    // Generate default title from filename
    const baseName = newFile.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');

    setFile({
      file: newFile,
      title: baseName,
      description: '',
      schematicType: 'full_schematic',
      sourceType: 'community',
      sourceUrl: '',
      version: '',
      pageCount: '',
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    handleFile(droppedFile);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const removeFile = () => {
    setFile(null);
  };

  const updateFile = (updates: Partial<PreviewFile>) => {
    if (file) {
      setFile({ ...file, ...updates });
    }
  };

  const handleUpload = () => {
    if (file && file.title.trim()) {
      uploadMutation.mutate(file);
    }
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return 'PDF';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')) return 'IMG';
    if (ext === 'zip') return 'ZIP';
    return 'DOC';
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      {!file && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={clsx(
            'border-2 border-dashed p-8 text-center cursor-pointer transition-all',
            isDragging
              ? 'border-cyber-green bg-cyber-green/10'
              : 'border-cyber-light/50 hover:border-cyber-green/50 hover:bg-cyber-dark/50'
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.zip"
            onChange={(e) => handleFile(e.target.files?.[0] || null)}
            className="hidden"
          />
          <FileText
            className={clsx(
              'h-10 w-10 mx-auto mb-3',
              isDragging ? 'text-cyber-green' : 'text-gray-500'
            )}
          />
          <p className="text-gray-400 mb-1">
            <span className="text-cyber-green">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-gray-600 font-mono">
            PDF, PNG, JPG, ZIP up to 50MB
          </p>
        </div>
      )}

      {/* File form */}
      {file && (
        <div className="card-cyber p-4 space-y-4">
          {/* File info header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-cyber-green/20 border border-cyber-green/30 flex items-center justify-center">
                <span className="text-cyber-green font-mono text-xs font-bold">
                  {getFileIcon(file.file.name)}
                </span>
              </div>
              <div>
                <div className="text-sm font-mono text-white truncate max-w-xs">
                  {file.file.name}
                </div>
                <div className="text-xs text-gray-500">
                  {(file.file.size / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>
            </div>
            <button
              onClick={removeFile}
              className="p-1 text-cyber-pink hover:bg-cyber-pink/20 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Title (required) */}
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              TITLE <span className="text-cyber-pink">*</span>
            </label>
            <input
              type="text"
              value={file.title}
              onChange={(e) => updateFile({ title: e.target.value })}
              placeholder="e.g., Main PCB Schematic Rev 2"
              className="input-cyber w-full"
            />
          </div>

          {/* Type and Source */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                SCHEMATIC TYPE
              </label>
              <select
                value={file.schematicType}
                onChange={(e) => updateFile({ schematicType: e.target.value })}
                className="input-cyber w-full"
              >
                {SCHEMATIC_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                SOURCE
              </label>
              <select
                value={file.sourceType}
                onChange={(e) => updateFile({ sourceType: e.target.value })}
                className="input-cyber w-full"
              >
                {SOURCE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Version and Page Count */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                VERSION
              </label>
              <input
                type="text"
                value={file.version}
                onChange={(e) => updateFile({ version: e.target.value })}
                placeholder="e.g., 1.2, Rev A"
                className="input-cyber w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                PAGE COUNT
              </label>
              <input
                type="number"
                value={file.pageCount}
                onChange={(e) => updateFile({ pageCount: e.target.value })}
                placeholder="For PDFs"
                min="1"
                className="input-cyber w-full"
              />
            </div>
          </div>

          {/* Source URL */}
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              SOURCE URL
            </label>
            <input
              type="url"
              value={file.sourceUrl}
              onChange={(e) => updateFile({ sourceUrl: e.target.value })}
              placeholder="https://..."
              className="input-cyber w-full"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              DESCRIPTION
            </label>
            <textarea
              value={file.description}
              onChange={(e) => updateFile({ description: e.target.value })}
              placeholder="Additional notes about this schematic..."
              rows={3}
              className="input-cyber w-full resize-none"
            />
          </div>

          {/* Upload button */}
          <div className="flex items-center justify-end pt-2">
            <button
              onClick={handleUpload}
              disabled={uploadMutation.isPending || !file.title.trim()}
              className={clsx(
                'btn-cyber btn-cyber-green flex items-center gap-2',
                (uploadMutation.isPending || !file.title.trim()) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  UPLOADING...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  UPLOAD SCHEMATIC
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Success message */}
      {uploadMutation.isSuccess && !file && (
        <div className="border border-cyber-green/50 bg-cyber-green/10 p-3 space-y-2">
          <div className="flex items-center gap-2 text-cyber-green text-sm font-mono">
            <CheckCircle className="h-4 w-4 shrink-0" />
            Schematic uploaded — pending moderator review.
          </div>
          <div className="flex items-start gap-2 text-xs text-gray-400 pl-6">
            <Clock className="h-3 w-3 text-cyber-cyan mt-0.5 shrink-0" />
            <span>It will appear once approved, usually within a few hours.</span>
          </div>
          <div className="flex items-start gap-2 text-xs text-gray-400 pl-6">
            <TrendingUp className="h-3 w-3 text-cyber-yellow mt-0.5 shrink-0" />
            <span>
              After{' '}
              <span className="text-white font-mono">25 contributions</span> and{' '}
              <span className="text-white font-mono">50 reputation</span>,
              uploads publish instantly.
            </span>
          </div>
        </div>
      )}

      {/* Error message */}
      {uploadMutation.isError && (
        <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
          <AlertCircle className="h-4 w-4" />
          Failed to upload schematic. Please try again.
        </div>
      )}
    </div>
  );
}
