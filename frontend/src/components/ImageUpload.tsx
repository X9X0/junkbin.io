import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { products, bgRemoval } from '../api/endpoints';
import { Upload, Camera, X, Loader2, CheckCircle, AlertCircle, Clock, TrendingUp } from 'lucide-react';
import clsx from 'clsx';
import axios from 'axios';
import BackgroundRemovalPanel, { BgRemovalState, DEFAULT_BG_REMOVAL_PARAMS } from './BackgroundRemovalPanel';
import { BG_REMOVAL_ELIGIBLE_IMAGE_TYPES } from '../constants/bgRemoval';

const isBgRemovalEligible = (imageType: string) => BG_REMOVAL_ELIGIBLE_IMAGE_TYPES.includes(imageType);

interface ImageTypeOption {
  value: string;
  label: string;
}

interface ImageUploadProps {
  productId?: string;
  uploadFn?: (formData: FormData) => Promise<any>;
  invalidateKey?: string[];
  imageTypes?: ImageTypeOption[];
  defaultImageType?: string;
  onSuccess?: () => void;
}

interface PreviewFile {
  file: File;
  preview: string;
  caption: string;
  imageType: string;
}

const PRODUCT_IMAGE_TYPES: ImageTypeOption[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'pcb_top', label: 'PCB Front' },
  { value: 'pcb_bottom', label: 'PCB Back' },
  { value: 'closeup', label: 'Close-up' },
  { value: 'label', label: 'Label/FCC ID' },
  { value: 'internal', label: 'Internals' },
  { value: 'ports', label: 'Ports/Connectors' },
  { value: 'damage', label: 'Damage/Issue' },
  { value: 'other', label: 'Other' },
];

export const COMPONENT_IMAGE_TYPES: ImageTypeOption[] = [
  { value: 'package', label: 'Package Photo' },
  { value: 'markings', label: 'Markings/Labels' },
  { value: 'closeup', label: 'Close-up Detail' },
  { value: 'pinout', label: 'Pinout Reference' },
  { value: 'application', label: 'Application/In-Circuit' },
  { value: 'other', label: 'Other' },
];

export default function ImageUpload({
  productId,
  uploadFn,
  invalidateKey,
  imageTypes,
  defaultImageType,
  onSuccess,
}: ImageUploadProps) {
  const types = imageTypes || PRODUCT_IMAGE_TYPES;
  const defaultType = defaultImageType || types[0].value;
  const queryKey = invalidateKey || (productId ? ['product', productId] : []);

  const [files, setFiles] = useState<PreviewFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [uploadedApproved, setUploadedApproved] = useState(true);
  const [bgRemovals, setBgRemovals] = useState<Record<string, BgRemovalState>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const doUpload = uploadFn || (productId
    ? (formData: FormData) => products.uploadImage(productId, formData)
    : undefined);

  const uploadMutation = useMutation({
    mutationFn: async (previewFile: PreviewFile) => {
      if (!doUpload) throw new Error('No upload function configured');

      let imageToUpload: File = previewFile.file;
      let backgroundRemoved = false;
      const bg = bgRemovals[previewFile.preview];
      if (isBgRemovalEligible(previewFile.imageType) && bg?.status === 'done' && bg.useProcessed && bg.resultUrl) {
        const blob = await fetch(bg.resultUrl).then((r) => r.blob());
        const baseName = previewFile.file.name.replace(/\.[^.]+$/, '');
        imageToUpload = new File([blob], `${baseName}.png`, { type: 'image/png' });
        backgroundRemoved = true;
      }

      const formData = new FormData();
      formData.append('image', imageToUpload);
      formData.append('image_type', previewFile.imageType);
      if (backgroundRemoved) {
        formData.append('background_removed', 'true');
      }
      if (previewFile.caption) {
        formData.append('caption', previewFile.caption);
      }
      return doUpload(formData);
    },
    onSuccess: () => {
      if (queryKey.length > 0) {
        queryClient.invalidateQueries({ queryKey });
      }
    },
  });

  // Kicks off auto background removal for an eligible (hero/package shot)
  // file the first time it becomes eligible - a no-op if already started.
  const maybeStartBgRemoval = (previewFile: PreviewFile) => {
    if (!isBgRemovalEligible(previewFile.imageType)) return;
    if (bgRemovals[previewFile.preview]) return;

    setBgRemovals((prev) => ({
      ...prev,
      [previewFile.preview]: {
        id: '',
        status: 'pending',
        resultUrl: null,
        error: null,
        useProcessed: true,
        ...DEFAULT_BG_REMOVAL_PARAMS,
      },
    }));

    bgRemoval.create(previewFile.file)
      .then((result) => {
        setBgRemovals((prev) => ({
          ...prev,
          [previewFile.preview]: { ...prev[previewFile.preview], id: result.id },
        }));
      })
      .catch(() => {
        setBgRemovals((prev) => ({
          ...prev,
          [previewFile.preview]: {
            ...prev[previewFile.preview],
            status: 'failed',
            error: 'Could not start background removal.',
          },
        }));
      });
  };

  const handleFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;

    const validFiles = Array.from(newFiles).filter((file) => {
      if (!file.type.startsWith('image/')) return false;
      if (file.size > 10 * 1024 * 1024) return false;
      return true;
    });

    const previews: PreviewFile[] = validFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      caption: '',
      imageType: defaultType,
    }));

    setFiles((prev) => [...prev, ...previews]);
    previews.forEach(maybeStartBgRemoval);
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
      const [removed] = newFiles.splice(index, 1);
      URL.revokeObjectURL(removed.preview);
      setBgRemovals((prevBg) => {
        const { [removed.preview]: _discard, ...rest } = prevBg;
        return rest;
      });
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

  const getUploadErrorMessage = (error: unknown): string => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const data = error.response?.data;

      if (status === 429) {
        return "You've hit the upload rate limit — wait a bit before uploading more.";
      }
      if (status === 401) {
        return 'Your session expired — please log in again.';
      }
      if (status === 403 && typeof data?.detail === 'string') {
        return data.detail;
      }
      if (data && typeof data === 'object') {
        const fieldError = Object.values(data).flat().find((v) => typeof v === 'string');
        if (fieldError) {
          return fieldError;
        }
      }
    }
    return 'Failed to upload image.';
  };

  const uploadAll = async () => {
    setUploadProgress(0);
    setUploadError(null);
    let completed = 0;
    let allApproved = true;
    const remaining: PreviewFile[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const result = await uploadMutation.mutateAsync(file);
        if (!result?.is_approved) allApproved = false;
        completed++;
        URL.revokeObjectURL(file.preview);
        setUploadProgress(Math.round((completed / files.length) * 100));
      } catch (error) {
        console.error('Failed to upload:', file.file.name, error);
        // Once one request is rate-limited the rest will be too — stop
        // burning the budget and keep every un-uploaded file for retry.
        if (axios.isAxiosError(error) && error.response?.status === 429) {
          setUploadError(getUploadErrorMessage(error));
          remaining.push(...files.slice(i));
          break;
        }
        setUploadError(getUploadErrorMessage(error));
        remaining.push(file);
      }
    }

    setFiles(remaining);
    setUploadProgress(null);
    setUploadedCount(completed);
    setUploadedApproved(allApproved);
    if (completed > 0) {
      onSuccess?.();
    }
  };

  return (
    <div className="space-y-4">
      {/* Drop zone + camera */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={clsx(
            'border-2 border-dashed p-8 text-center cursor-pointer transition-all flex-1',
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

        {/* Camera capture button */}
        <div
          onClick={() => cameraInputRef.current?.click()}
          className="border-2 border-dashed border-cyber-light/50 hover:border-cyber-cyan/50 hover:bg-cyber-dark/50 p-8 text-center cursor-pointer transition-all sm:w-48"
        >
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => {
              handleFiles(e.target.files);
              e.target.value = '';
            }}
            className="hidden"
          />
          <Camera className="h-10 w-10 mx-auto mb-3 text-gray-500" />
          <p className="text-gray-400 mb-1">
            <span className="text-cyber-cyan">Take Photo</span>
          </p>
          <p className="text-xs text-gray-600 font-mono">
            Use camera
          </p>
        </div>
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
                  onChange={(e) => {
                    const imageType = e.target.value;
                    updateFile(index, { imageType });
                    maybeStartBgRemoval({ ...file, imageType });
                  }}
                  className="input-cyber text-sm py-1 mb-2"
                >
                  {types.map((type) => (
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

                {/* Auto background removal (hero/package shots only) */}
                {isBgRemovalEligible(file.imageType) && bgRemovals[file.preview] && (
                  <BackgroundRemovalPanel
                    originalPreviewUrl={file.preview}
                    state={bgRemovals[file.preview]}
                    onChange={(updates) =>
                      setBgRemovals((prev) => ({
                        ...prev,
                        [file.preview]: { ...prev[file.preview], ...updates },
                      }))
                    }
                  />
                )}
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
      {uploadedCount > 0 && !uploadMutation.isPending && (
        <div className="border border-cyber-green/50 bg-cyber-green/10 p-3 space-y-2">
          <div className="flex items-center gap-2 text-cyber-green text-sm font-mono">
            <CheckCircle className="h-4 w-4 shrink-0" />
            {uploadedApproved
              ? <>{uploadedCount} image{uploadedCount !== 1 ? 's' : ''} uploaded and published.</>
              : <>{uploadedCount} image{uploadedCount !== 1 ? 's' : ''} uploaded — pending moderator review.</>}
          </div>
          {uploadedApproved ? (
            <div className="flex items-start gap-2 text-xs text-gray-400 pl-6">
              <CheckCircle className="h-3 w-3 text-cyber-green mt-0.5 shrink-0" />
              <span>You're a trusted contributor, so these went live instantly.</span>
            </div>
          ) : (
            <>
              <div className="flex items-start gap-2 text-xs text-gray-400 pl-6">
                <Clock className="h-3 w-3 text-cyber-cyan mt-0.5 shrink-0" />
                <span>They will appear once approved, usually within a few hours.</span>
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
            </>
          )}
        </div>
      )}

      {/* Error message */}
      {uploadError && !uploadMutation.isPending && (
        <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
          <AlertCircle className="h-4 w-4" />
          {uploadError}
          {files.length > 0 && ' Remaining images were kept — click Upload All to retry.'}
        </div>
      )}
    </div>
  );
}
