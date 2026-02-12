import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, AlertTriangle, CheckCircle, XCircle, MinusCircle } from 'lucide-react';
import { reports } from '../../api/endpoints';
import type { Report } from '../../types';
import clsx from 'clsx';

interface ResolveReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: Report;
}

const actions = [
  {
    value: 'valid',
    label: 'Valid',
    description: 'Report is valid — applies a strike to the reported user',
    icon: CheckCircle,
    color: 'text-cyber-green border-cyber-green',
  },
  {
    value: 'invalid',
    label: 'Invalid',
    description: 'Report is not valid — no action taken against reported user',
    icon: XCircle,
    color: 'text-cyber-pink border-cyber-pink',
  },
  {
    value: 'dismiss',
    label: 'Dismiss',
    description: 'Dismiss without full review',
    icon: MinusCircle,
    color: 'text-gray-400 border-gray-500',
  },
];

export default function ResolveReportModal({ isOpen, onClose, report }: ResolveReportModalProps) {
  const [action, setAction] = useState('valid');
  const [notes, setNotes] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => reports.resolve(report.id, { action, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      queryClient.invalidateQueries({ queryKey: ['reportStats'] });
      onClose();
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-cyber-dark border border-cyber-light/30 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg text-white">
            RESOLVE <span className="text-cyber-yellow">REPORT</span>
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Report details */}
        <div className="px-6 py-4 space-y-3 border-b border-cyber-light/20">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500 font-mono text-xs">REPORTER</span>
              <p className="text-white">{report.reporter?.username || 'Unknown'}</p>
            </div>
            <div>
              <span className="text-gray-500 font-mono text-xs">REPORTED USER</span>
              <p className="text-white">{report.reported_user?.username || 'N/A'}</p>
            </div>
            <div>
              <span className="text-gray-500 font-mono text-xs">REASON</span>
              <p className="text-cyber-yellow">{report.reason_display}</p>
            </div>
            <div>
              <span className="text-gray-500 font-mono text-xs">CONTENT TYPE</span>
              <p className="text-gray-300">{report.content_type_name}</p>
            </div>
          </div>
          {report.reported_item_data && (
            <div>
              <span className="text-gray-500 font-mono text-xs">REPORTED ITEM</span>
              <p className="text-cyber-cyan text-sm">{report.reported_item_data.display}</p>
            </div>
          )}
          <div>
            <span className="text-gray-500 font-mono text-xs">DESCRIPTION</span>
            <p className="text-gray-300 text-sm mt-1">{report.description}</p>
          </div>
        </div>

        {/* Action selection */}
        <div className="px-6 py-4 space-y-3">
          <label className="font-mono text-xs text-gray-500">ACTION</label>
          <div className="space-y-2">
            {actions.map((a) => (
              <label
                key={a.value}
                className={clsx(
                  'flex items-start gap-3 p-3 border cursor-pointer transition-colors',
                  action === a.value
                    ? a.color + ' bg-cyber-light/10'
                    : 'border-cyber-light/20 hover:border-cyber-light/40'
                )}
              >
                <input
                  type="radio"
                  name="action"
                  value={a.value}
                  checked={action === a.value}
                  onChange={() => setAction(a.value)}
                  className="sr-only"
                />
                <a.icon className={clsx('h-5 w-5 mt-0.5 flex-shrink-0', action === a.value ? '' : 'text-gray-600')} />
                <div>
                  <p className={clsx('font-mono text-sm', action === a.value ? 'text-white' : 'text-gray-400')}>
                    {a.label}
                  </p>
                  <p className="text-xs text-gray-500">{a.description}</p>
                </div>
              </label>
            ))}
          </div>

          <div>
            <label className="font-mono text-xs text-gray-500">RESOLUTION NOTES</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes about the resolution..."
              rows={3}
              className="input-cyber w-full mt-1 resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-cyber-light/30 flex items-center justify-between">
          {mutation.isError && (
            <p className="text-cyber-pink text-sm flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" />
              Failed to resolve report
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
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="btn-cyber text-sm py-2"
            >
              {mutation.isPending ? 'RESOLVING...' : 'RESOLVE'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
