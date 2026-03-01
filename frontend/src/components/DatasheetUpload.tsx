import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, X, Loader2, CheckCircle, AlertCircle, FileText } from 'lucide-react';

const SOURCE_TYPES = [
  { value: 'official',    label: 'Official Manufacturer' },
  { value: 'community',   label: 'Community Upload' },
  { value: 'mirror',      label: 'Third-party Mirror' },
  { value: 'reverse_eng', label: 'Reverse Engineered' },
];

interface DatasheetUploadProps {
  uploadFn: (formData: FormData) => Promise<any>;
  invalidateKey: string[];
  onSuccess?: () => void;
}

export default function DatasheetUpload({ uploadFn, invalidateKey, onSuccess }: DatasheetUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [version, setVersion] = useState('');
  const [sourceType, setSourceType] = useState('official');
  const [sourceUrl, setSourceUrl] = useState('');
  const [sourceNotes, setSourceNotes] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file || !title.trim()) throw new Error('File and title are required');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title.trim());
      formData.append('source_type', sourceType);
      if (version.trim()) formData.append('version', version.trim());
      if (sourceUrl.trim()) formData.append('source_url', sourceUrl.trim());
      if (sourceNotes.trim()) formData.append('source_notes', sourceNotes.trim());
      return uploadFn(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invalidateKey });
      setFile(null);
      setTitle('');
      setVersion('');
      setSourceType('official');
      setSourceUrl('');
      setSourceNotes('');
      onSuccess?.();
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    if (selected && !title) {
      // Auto-fill title from filename (strip extension)
      setTitle(selected.name.replace(/\.[^.]+$/, ''));
    }
  };

  return (
    <div className="space-y-4">
      {/* File picker */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-cyber-light/50 hover:border-cyber-cyan/50 hover:bg-cyber-dark/50 p-6 text-center cursor-pointer transition-all"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.svg"
          onChange={handleFileChange}
          className="hidden"
        />
        {file ? (
          <div className="flex items-center justify-center gap-3">
            <FileText className="h-6 w-6 text-cyber-cyan" />
            <div className="text-left">
              <p className="text-white text-sm font-mono">{file.name}</p>
              <p className="text-gray-500 text-xs font-mono">
                {(file.size / 1024).toFixed(0)} KB
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="ml-2 text-cyber-pink hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="h-8 w-8 mx-auto mb-2 text-gray-500" />
            <p className="text-gray-400 text-sm">
              <span className="text-cyber-cyan">Click to select</span> a datasheet
            </p>
            <p className="text-xs text-gray-600 font-mono mt-1">PDF, PNG, JPG, SVG</p>
          </>
        )}
      </div>

      {/* Metadata fields */}
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-mono text-gray-500 mb-1">Title *</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. STM32F4 Reference Manual"
            className="input-cyber text-sm py-1.5 w-full"
          />
        </div>
        <div>
          <label className="block text-xs font-mono text-gray-500 mb-1">Version</label>
          <input
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="e.g. Rev 7, 2023-Q4"
            className="input-cyber text-sm py-1.5 w-full"
          />
        </div>
        <div>
          <label className="block text-xs font-mono text-gray-500 mb-1">Source Type</label>
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            className="input-cyber text-sm py-1.5 w-full"
          >
            {SOURCE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-mono text-gray-500 mb-1">Source URL</label>
          <input
            type="url"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://..."
            className="input-cyber text-sm py-1.5 w-full"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-mono text-gray-500 mb-1">Notes</label>
        <textarea
          value={sourceNotes}
          onChange={(e) => setSourceNotes(e.target.value)}
          placeholder="Additional notes about this datasheet (optional)"
          rows={2}
          className="input-cyber text-sm py-1.5 w-full resize-none"
        />
      </div>

      {/* Upload button */}
      <div className="flex items-center justify-end">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !file || !title.trim()}
          className="btn-cyber flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              UPLOADING...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              UPLOAD DATASHEET
            </>
          )}
        </button>
      </div>

      {mutation.isSuccess && (
        <div className="flex items-center gap-2 p-3 border border-cyber-green/50 bg-cyber-green/10 text-cyber-green text-sm font-mono">
          <CheckCircle className="h-4 w-4" />
          Datasheet uploaded successfully! It will appear after review.
        </div>
      )}

      {mutation.isError && (
        <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
          <AlertCircle className="h-4 w-4" />
          {(mutation.error as Error)?.message || 'Upload failed. Please try again.'}
        </div>
      )}
    </div>
  );
}
