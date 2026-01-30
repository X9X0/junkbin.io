import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import api from '../api/client';
import { X, AlertTriangle, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  contentType: 'products.product' | 'components.component' | 'products.schematic';
  objectId: string;
  itemName?: string;
}

const REPORT_REASONS = [
  { value: 'incorrect_info', label: 'Incorrect Information', description: 'The information is wrong or misleading' },
  { value: 'duplicate', label: 'Duplicate Entry', description: 'This is a duplicate of another entry' },
  { value: 'spam', label: 'Spam/Advertising', description: 'This appears to be spam or advertising' },
  { value: 'inappropriate', label: 'Inappropriate Content', description: 'This content is inappropriate' },
  { value: 'copyright', label: 'Copyright Violation', description: 'This violates copyright' },
  { value: 'other', label: 'Other', description: 'Other issue not listed above' },
];

export default function ReportModal({
  isOpen,
  onClose,
  contentType,
  objectId,
  itemName,
}: ReportModalProps) {
  const [reason, setReason] = useState('');
  const [description, setDescription] = useState('');

  const reportMutation = useMutation({
    mutationFn: async (data: { content_type: string; object_id: string; reason: string; description: string }) => {
      const response = await api.post('/reports/', data);
      return response.data;
    },
    onSuccess: () => {
      setTimeout(() => {
        onClose();
        setReason('');
        setDescription('');
      }, 2000);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (reason && description.trim()) {
      reportMutation.mutate({
        content_type: contentType,
        object_id: objectId,
        reason,
        description: description.trim(),
      });
    }
  };

  if (!isOpen) return null;

  const contentTypeLabel = contentType === 'products.product'
    ? 'product'
    : contentType === 'components.component'
    ? 'component'
    : 'schematic';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg card-cyber p-6">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-cyber-yellow/20 border border-cyber-yellow/50">
            <AlertTriangle className="h-6 w-6 text-cyber-yellow" />
          </div>
          <div>
            <h2 className="font-display text-xl font-bold text-white">
              REPORT {contentTypeLabel.toUpperCase()}
            </h2>
            {itemName && (
              <p className="text-sm text-gray-500 font-mono truncate max-w-xs">
                {itemName}
              </p>
            )}
          </div>
        </div>

        {/* Success state */}
        {reportMutation.isSuccess ? (
          <div className="text-center py-8">
            <CheckCircle className="h-16 w-16 text-cyber-green mx-auto mb-4" />
            <h3 className="font-display text-lg text-white mb-2">REPORT SUBMITTED</h3>
            <p className="text-gray-400 text-sm">
              Thank you for helping improve the database. Our moderators will review your report.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Reason selection */}
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-2">
                REASON FOR REPORT <span className="text-cyber-pink">*</span>
              </label>
              <div className="space-y-2">
                {REPORT_REASONS.map((r) => (
                  <label
                    key={r.value}
                    className={clsx(
                      'flex items-start gap-3 p-3 border cursor-pointer transition-all',
                      reason === r.value
                        ? 'border-cyber-yellow bg-cyber-yellow/10'
                        : 'border-cyber-light/30 hover:border-cyber-light/50'
                    )}
                  >
                    <input
                      type="radio"
                      name="reason"
                      value={r.value}
                      checked={reason === r.value}
                      onChange={(e) => setReason(e.target.value)}
                      className="mt-1 accent-cyber-yellow"
                    />
                    <div>
                      <div className="text-white text-sm">{r.label}</div>
                      <div className="text-xs text-gray-500">{r.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-2">
                DESCRIPTION <span className="text-cyber-pink">*</span>
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Please provide details about the issue..."
                rows={4}
                className="input-cyber resize-none"
                required
              />
              <p className="text-xs text-gray-600 mt-1">
                Be specific about what's wrong and how it should be corrected.
              </p>
            </div>

            {/* Error message */}
            {reportMutation.isError && (
              <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                Failed to submit report. Please try again.
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-4 pt-4 border-t border-cyber-light/30">
              <button
                type="button"
                onClick={onClose}
                className="text-gray-400 hover:text-white text-sm font-mono"
              >
                CANCEL
              </button>
              <button
                type="submit"
                disabled={!reason || !description.trim() || reportMutation.isPending}
                className={clsx(
                  'btn-cyber flex items-center gap-2',
                  (!reason || !description.trim() || reportMutation.isPending) &&
                    'opacity-50 cursor-not-allowed'
                )}
              >
                {reportMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    SUBMITTING...
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-4 w-4" />
                    SUBMIT REPORT
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
