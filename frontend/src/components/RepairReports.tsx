import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { Trash2, Wrench, AlertCircle, ThumbsUp, ThumbsDown, CheckCircle2, HelpCircle } from 'lucide-react';
import clsx from 'clsx';
import { parseApiError } from '../utils/formErrors';
import type { RepairReport, RepairReportVoteType } from '../types';

function timeAgo(dateString: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

const emptyForm = {
  title: '',
  symptom: '',
  diagnostics: '',
  resolution: '',
  status: 'unresolved' as 'unresolved' | 'resolved',
  product_component: '',
};

export default function RepairReports({ productId }: { productId: string }) {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['product', productId, 'repairs', page],
    queryFn: () => products.repairs(productId, page),
  });

  const { data: componentOptions } = useQuery({
    queryKey: ['product', productId, 'components'],
    queryFn: () => products.components(productId),
    enabled: showForm,
  });

  const addMutation = useMutation({
    mutationFn: () =>
      products.addRepairReport(productId, {
        title: form.title.trim(),
        symptom: form.symptom.trim(),
        diagnostics: form.diagnostics.trim(),
        resolution: form.resolution.trim(),
        status: form.status,
        product_component: form.product_component || null,
      }),
    onSuccess: () => {
      setForm(emptyForm);
      setShowForm(false);
      setError('');
      setPage(1);
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'repairs'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to post repair report. Please try again.'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (reportId: string) => products.deleteRepairReport(productId, reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'repairs'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    },
  });

  const voteMutation = useMutation({
    mutationFn: ({ reportId, voteType, current }: { reportId: string; voteType: RepairReportVoteType; current: RepairReportVoteType | null }) =>
      current === voteType
        ? products.removeRepairReportVote(productId, reportId)
        : products.voteRepairReport(productId, reportId, voteType),
    onSuccess: (updated) => {
      queryClient.setQueryData(['product', productId, 'repairs', page], (old: any) => {
        if (!old) return old;
        return {
          ...old,
          results: old.results.map((r: RepairReport) => (r.id === updated.id ? updated : r)),
        };
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.symptom.trim()) return;
    if (form.status === 'resolved' && !form.resolution.trim()) {
      setError('Resolution is required to mark a repair as resolved.');
      return;
    }
    addMutation.mutate();
  };

  const canDelete = (authorId: string) => {
    if (!user) return false;
    return user.id === authorId || user.is_moderator;
  };

  return (
    <div className="space-y-6">
      {isAuthenticated ? (
        <div className="card-cyber p-4">
          {!showForm ? (
            <button onClick={() => setShowForm(true)} className="btn-cyber text-sm py-1.5">
              WRITE A REPAIR REPORT
            </button>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Short summary — e.g. USB-C stuck at 5V, no negotiation"
                maxLength={200}
                className="input-cyber w-full"
              />
              <textarea
                value={form.symptom}
                onChange={(e) => setForm((f) => ({ ...f, symptom: e.target.value }))}
                placeholder="Symptom — what's wrong, observed behavior"
                rows={2}
                className="input-cyber w-full resize-none"
              />
              <textarea
                value={form.diagnostics}
                onChange={(e) => setForm((f) => ({ ...f, diagnostics: e.target.value }))}
                placeholder="Diagnostics — tools used and readings taken (optional)"
                rows={2}
                className="input-cyber w-full resize-none"
              />
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-xs font-mono text-gray-400">
                  <input
                    type="checkbox"
                    checked={form.status === 'resolved'}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, status: e.target.checked ? 'resolved' : 'unresolved' }))
                    }
                  />
                  Mark as resolved
                </label>
              </div>
              {form.status === 'resolved' && (
                <textarea
                  value={form.resolution}
                  onChange={(e) => setForm((f) => ({ ...f, resolution: e.target.value }))}
                  placeholder="Resolution — what fixed it"
                  rows={2}
                  className="input-cyber w-full resize-none"
                />
              )}
              {componentOptions && componentOptions.length > 0 && (
                <select
                  value={form.product_component}
                  onChange={(e) => setForm((f) => ({ ...f, product_component: e.target.value }))}
                  className="input-cyber w-full text-sm"
                >
                  <option value="">Not tied to a specific component (optional)</option>
                  {componentOptions.map((pc: any) => (
                    <option key={pc.id} value={pc.id}>
                      {pc.reference_designator || '—'} · {pc.component?.part_number || pc.component?.manufacturer || 'component'}
                    </option>
                  ))}
                </select>
              )}
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setForm(emptyForm);
                    setError('');
                  }}
                  className="text-xs text-gray-500 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!form.title.trim() || !form.symptom.trim() || addMutation.isPending}
                  className="btn-cyber text-sm py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {addMutation.isPending ? 'POSTING...' : 'POST REPAIR REPORT'}
                </button>
              </div>
              {error && (
                <div className="flex items-center gap-2 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />
                  {error}
                </div>
              )}
            </form>
          )}
        </div>
      ) : (
        <div className="card-cyber p-6 text-center">
          <Wrench className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400 mb-3 text-sm">Log in to share a repair report.</p>
          <Link to="/login" className="btn-cyber text-sm">
            LOGIN
          </Link>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card-cyber p-4 animate-pulse">
              <div className="h-4 w-1/2 bg-cyber-light/20 rounded mb-2" />
              <div className="h-3 w-full bg-cyber-light/10 rounded mb-1" />
              <div className="h-3 w-2/3 bg-cyber-light/10 rounded" />
            </div>
          ))}
        </div>
      ) : data && data.results.length > 0 ? (
        <div className="space-y-3">
          {data.results.map((report) => (
            <div key={report.id} className="card-cyber p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-mono text-sm text-white break-words">{report.title}</h4>
                    <span
                      className={clsx(
                        'flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded-full flex-shrink-0',
                        report.status === 'resolved'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-cyber-yellow/20 text-cyber-yellow'
                      )}
                    >
                      {report.status === 'resolved' ? (
                        <CheckCircle2 className="h-3 w-3" />
                      ) : (
                        <HelpCircle className="h-3 w-3" />
                      )}
                      {report.status_display}
                    </span>
                    {!report.is_approved && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-gray-500/20 text-gray-400">
                        Pending review
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-600">
                    <span>{report.author?.username || 'deleted'}</span>
                    <span>{timeAgo(report.created_at)}</span>
                    {report.product_component && (
                      <span className="text-cyber-cyan">
                        {report.product_component.reference_designator}
                      </span>
                    )}
                  </div>
                </div>
                {report.author && canDelete(report.author.id) && (
                  <button
                    onClick={() => {
                      if (confirm('Delete this repair report?')) {
                        deleteMutation.mutate(report.id);
                      }
                    }}
                    className="text-gray-600 hover:text-red-400 transition-colors flex-shrink-0 p-1"
                    title="Delete repair report"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              <dl className="mt-3 space-y-2 text-sm">
                <div>
                  <dt className="text-xs font-mono text-gray-500">SYMPTOM</dt>
                  <dd className="text-gray-300 whitespace-pre-wrap break-words">{report.symptom}</dd>
                </div>
                {report.diagnostics && (
                  <div>
                    <dt className="text-xs font-mono text-gray-500">DIAGNOSTICS</dt>
                    <dd className="text-gray-300 whitespace-pre-wrap break-words">{report.diagnostics}</dd>
                  </div>
                )}
                {report.resolution && (
                  <div>
                    <dt className="text-xs font-mono text-gray-500">RESOLUTION</dt>
                    <dd className="text-gray-300 whitespace-pre-wrap break-words">{report.resolution}</dd>
                  </div>
                )}
              </dl>

              {isAuthenticated && report.author?.id !== user?.id && (
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-cyber-light/20">
                  <button
                    onClick={() =>
                      voteMutation.mutate({ reportId: report.id, voteType: 'helpful', current: report.user_vote })
                    }
                    className={clsx(
                      'flex items-center gap-1 text-xs font-mono transition-colors',
                      report.user_vote === 'helpful' ? 'text-cyber-cyan' : 'text-gray-500 hover:text-white'
                    )}
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                    {report.helpful_count}
                  </button>
                  <button
                    onClick={() =>
                      voteMutation.mutate({ reportId: report.id, voteType: 'not_helpful', current: report.user_vote })
                    }
                    className={clsx(
                      'flex items-center gap-1 text-xs font-mono transition-colors',
                      report.user_vote === 'not_helpful' ? 'text-red-400' : 'text-gray-500 hover:text-white'
                    )}
                  >
                    <ThumbsDown className="h-3.5 w-3.5" />
                    {report.unhelpful_count}
                  </button>
                </div>
              )}
            </div>
          ))}

          {data.count > data.results.length && (
            <div className="flex justify-center gap-3 pt-2">
              {data.previous && (
                <button onClick={() => setPage((p) => p - 1)} className="btn-cyber text-xs py-1.5">
                  NEWER
                </button>
              )}
              {data.next && (
                <button onClick={() => setPage((p) => p + 1)} className="btn-cyber text-xs py-1.5">
                  OLDER
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <Wrench className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No repair reports yet — be the first to document a fix.</p>
        </div>
      )}
    </div>
  );
}
