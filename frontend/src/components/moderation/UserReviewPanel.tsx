import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { X, AlertTriangle, Shield, Clock } from 'lucide-react';
import { reviews } from '../../api/endpoints';

import clsx from 'clsx';

interface UserReviewPanelProps {
  isOpen: boolean;
  onClose: () => void;
  reviewId: string;
}

const statusOptions = [
  {
    value: 'cleared',
    label: 'Cleared',
    description: 'No action needed',
    color: 'text-cyber-green border-cyber-green',
  },
  {
    value: 'warning_issued',
    label: 'Warning Issued',
    description: 'User warned about behavior',
    color: 'text-cyber-yellow border-cyber-yellow',
  },
  {
    value: 'restricted',
    label: 'Restricted',
    description: 'Removes trusted status — user submissions will require review',
    color: 'text-orange-400 border-orange-400',
    warning: true,
  },
  {
    value: 'suspended',
    label: 'Suspended',
    description: 'Deactivates user account entirely',
    color: 'text-red-500 border-red-500',
    warning: true,
  },
];

export default function UserReviewPanel({ isOpen, onClose, reviewId }: UserReviewPanelProps) {
  const [status, setStatus] = useState('cleared');
  const [notes, setNotes] = useState('');
  const [actionTaken, setActionTaken] = useState('');
  const queryClient = useQueryClient();

  const { data: review, isLoading } = useQuery({
    queryKey: ['userReview', reviewId],
    queryFn: () => reviews.get(reviewId),
    enabled: isOpen,
  });

  const startMutation = useMutation({
    mutationFn: () => reviews.start(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userReview', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['userReviews'] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => reviews.complete(reviewId, { status, notes, action_taken: actionTaken }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userReviews'] });
      queryClient.invalidateQueries({ queryKey: ['userReview', reviewId] });
      onClose();
    },
  });

  if (!isOpen) return null;

  const isCompleted = review && !['pending', 'in_progress'].includes(review.status);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-cyber-dark border border-cyber-light/30 shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-cyber-light/30 bg-cyber-dark z-10">
          <h2 className="font-display text-lg text-white">
            USER <span className="text-cyber-yellow">REVIEW</span>
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="px-6 py-12 text-center text-gray-500">Loading review details...</div>
        ) : review ? (
          <>
            {/* User info */}
            <div className="px-6 py-4 border-b border-cyber-light/20">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 font-mono text-xs">USER</span>
                  <p className="text-white font-medium">{review.user.username}</p>
                </div>
                <div>
                  <span className="text-gray-500 font-mono text-xs">TYPE</span>
                  <p className="text-gray-300">{review.review_type_display}</p>
                </div>
                <div>
                  <span className="text-gray-500 font-mono text-xs">STRIKES</span>
                  <p className="text-cyber-pink font-mono">{review.trigger_report_count}</p>
                </div>
                <div>
                  <span className="text-gray-500 font-mono text-xs">STATUS</span>
                  <p className={clsx(
                    'font-mono text-sm',
                    review.status === 'pending' ? 'text-cyber-yellow' :
                    review.status === 'in_progress' ? 'text-cyber-cyan' :
                    'text-gray-400'
                  )}>
                    {review.status_display}
                  </p>
                </div>
              </div>
            </div>

            {/* Related reports */}
            {review.related_reports && review.related_reports.length > 0 && (
              <div className="px-6 py-4 border-b border-cyber-light/20">
                <h3 className="font-mono text-xs text-gray-500 mb-3">RELATED REPORTS ({review.related_reports.length})</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {review.related_reports.map((report) => (
                    <div key={report.id} className="flex items-center justify-between p-2 bg-cyber-gray/50 border border-cyber-light/10 text-sm">
                      <div className="flex items-center gap-3">
                        <span className="text-cyber-yellow font-mono text-xs">{report.reason_display}</span>
                        <span className="text-gray-400 truncate max-w-xs">{report.description}</span>
                      </div>
                      <span className={clsx(
                        'font-mono text-xs px-2 py-0.5 border',
                        report.status === 'resolved_valid' ? 'border-cyber-green/50 text-cyber-green' :
                        report.status === 'resolved_invalid' ? 'border-cyber-pink/50 text-cyber-pink' :
                        'border-gray-600 text-gray-500'
                      )}>
                        {report.status_display}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            {!isCompleted ? (
              <div className="px-6 py-4 space-y-4">
                {/* Start review button */}
                {review.status === 'pending' && (
                  <button
                    onClick={() => startMutation.mutate()}
                    disabled={startMutation.isPending}
                    className="w-full flex items-center justify-center gap-2 py-2 border border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan/10 font-mono text-sm transition-colors"
                  >
                    <Clock className="h-4 w-4" />
                    {startMutation.isPending ? 'STARTING...' : 'START REVIEW'}
                  </button>
                )}

                {/* Status selection */}
                <div>
                  <label className="font-mono text-xs text-gray-500">DECISION</label>
                  <div className="space-y-2 mt-2">
                    {statusOptions.map((opt) => (
                      <label
                        key={opt.value}
                        className={clsx(
                          'flex items-start gap-3 p-3 border cursor-pointer transition-colors',
                          status === opt.value
                            ? opt.color + ' bg-cyber-light/10'
                            : 'border-cyber-light/20 hover:border-cyber-light/40'
                        )}
                      >
                        <input
                          type="radio"
                          name="status"
                          value={opt.value}
                          checked={status === opt.value}
                          onChange={() => setStatus(opt.value)}
                          className="sr-only"
                        />
                        <Shield className={clsx('h-5 w-5 mt-0.5 flex-shrink-0', status === opt.value ? '' : 'text-gray-600')} />
                        <div>
                          <p className={clsx('font-mono text-sm', status === opt.value ? 'text-white' : 'text-gray-400')}>
                            {opt.label}
                          </p>
                          <p className={clsx('text-xs', opt.warning && status === opt.value ? 'text-red-400' : 'text-gray-500')}>
                            {opt.description}
                          </p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="font-mono text-xs text-gray-500">NOTES</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Internal notes about the review..."
                    rows={2}
                    className="input-cyber w-full mt-1 resize-none"
                  />
                </div>

                <div>
                  <label className="font-mono text-xs text-gray-500">ACTION TAKEN</label>
                  <textarea
                    value={actionTaken}
                    onChange={(e) => setActionTaken(e.target.value)}
                    placeholder="Description of action taken..."
                    rows={2}
                    className="input-cyber w-full mt-1 resize-none"
                  />
                </div>
              </div>
            ) : (
              /* Already completed */
              <div className="px-6 py-4 space-y-3">
                <div className="p-3 border border-cyber-light/20 bg-cyber-gray/30">
                  <span className="font-mono text-xs text-gray-500">REVIEWED BY</span>
                  <p className="text-white text-sm">{review.reviewer?.username || 'Unknown'}</p>
                </div>
                {review.notes && (
                  <div>
                    <span className="font-mono text-xs text-gray-500">NOTES</span>
                    <p className="text-gray-300 text-sm mt-1">{review.notes}</p>
                  </div>
                )}
                {review.action_taken && (
                  <div>
                    <span className="font-mono text-xs text-gray-500">ACTION TAKEN</span>
                    <p className="text-gray-300 text-sm mt-1">{review.action_taken}</p>
                  </div>
                )}
              </div>
            )}

            {/* Footer */}
            {!isCompleted && (
              <div className="px-6 py-4 border-t border-cyber-light/30 flex items-center justify-between">
                {completeMutation.isError && (
                  <p className="text-cyber-pink text-sm flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4" />
                    Failed to complete review
                  </p>
                )}
                <div className="flex gap-3 ml-auto">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 font-mono text-sm text-gray-400 border border-cyber-light/30 hover:text-white hover:border-cyber-light/50 transition-colors"
                  >
                    CANCEL
                  </button>
                  <button
                    onClick={() => completeMutation.mutate()}
                    disabled={completeMutation.isPending}
                    className={clsx(
                      'px-4 py-2 font-mono text-sm border transition-colors',
                      status === 'suspended'
                        ? 'border-red-500 text-red-500 hover:bg-red-500/10'
                        : status === 'restricted'
                        ? 'border-orange-400 text-orange-400 hover:bg-orange-400/10'
                        : 'btn-cyber'
                    )}
                  >
                    {completeMutation.isPending ? 'COMPLETING...' : 'COMPLETE REVIEW'}
                  </button>
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
