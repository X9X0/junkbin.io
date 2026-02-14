import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';
import { junkbin } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import {
  Package,
  Cpu,
  Trash2,
  Eye,
  EyeOff,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import clsx from 'clsx';
import type { JunkbinItem } from '../types';

const CONDITION_LABELS: Record<string, string> = {
  new: 'New',
  working: 'Working',
  broken: 'Broken / For Parts',
  unknown: 'Unknown',
};

const STATUS_LABELS: Record<string, string> = {
  available: 'For Trade',
  not_for_trade: 'Not for Trade',
};

export default function MyJunkbin() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'have' | 'want'>('have');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [filterContentType, setFilterContentType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [editData, setEditData] = useState<Record<string, Partial<JunkbinItem>>>({});

  const { data: summary } = useQuery({
    queryKey: ['junkbin', 'my-summary'],
    queryFn: () => junkbin.mySummary(),
    enabled: isAuthenticated,
  });

  const { data: items, isLoading } = useQuery({
    queryKey: ['junkbin', 'my-items', activeTab, filterContentType, filterStatus],
    queryFn: () =>
      junkbin.myItems({
        item_type: activeTab,
        ...(filterContentType && { content_type: filterContentType }),
        ...(filterStatus && { status: filterStatus }),
      }),
    enabled: isAuthenticated,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<JunkbinItem> }) =>
      junkbin.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['junkbin'] });
      setExpandedId(null);
      setEditData({});
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => junkbin.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['junkbin'] });
      setConfirmDelete(null);
    },
  });

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const itemsList = items?.results || [];

  const getEdit = (id: string) => editData[id] || {};
  const setEdit = (id: string, data: Partial<JunkbinItem>) => {
    setEditData((prev) => ({ ...prev, [id]: { ...prev[id], ...data } }));
  };

  const handleSave = (item: JunkbinItem) => {
    const changes = getEdit(item.id);
    if (Object.keys(changes).length === 0) {
      setExpandedId(null);
      return;
    }
    updateMutation.mutate({ id: item.id, data: changes });
  };

  return (
    <div className="py-8">
      <div className="mx-auto max-w-5xl px-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <h1 className="font-display text-3xl font-bold text-white">MY JUNKBIN</h1>
          {summary && (
            <div className="flex items-center gap-4 text-sm font-mono">
              <span className="text-cyber-green">
                {summary.have_count} <span className="text-gray-500">have</span>
              </span>
              <span className="text-cyber-yellow">
                {summary.want_count} <span className="text-gray-500">want</span>
              </span>
              <span className="text-cyber-cyan">
                {summary.available_count} <span className="text-gray-500">for trade</span>
              </span>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-cyber-light/30 mb-6">
          {(['have', 'want'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab);
                setExpandedId(null);
                setConfirmDelete(null);
              }}
              className={clsx(
                'py-3 px-6 font-mono text-sm border-b-2 transition-colors',
                activeTab === tab
                  ? tab === 'have'
                    ? 'border-cyber-green text-cyber-green'
                    : 'border-cyber-yellow text-cyber-yellow'
                  : 'border-transparent text-gray-500 hover:text-white'
              )}
            >
              {tab.toUpperCase()}
              {summary && (
                <span className="ml-2 text-xs opacity-60">
                  ({tab === 'have' ? summary.have_count : summary.want_count})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6">
          <select
            value={filterContentType}
            onChange={(e) => setFilterContentType(e.target.value)}
            className="bg-cyber-dark border border-cyber-light/50 px-3 py-1.5 text-sm text-white font-mono focus:border-cyber-cyan focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="product">Products</option>
            <option value="component">Components</option>
          </select>
          {activeTab === 'have' && (
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-cyber-dark border border-cyber-light/50 px-3 py-1.5 text-sm text-white font-mono focus:border-cyber-cyan focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="available">For Trade</option>
              <option value="not_for_trade">Not for Trade</option>
            </select>
          )}
        </div>

        {/* Items */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-cyber-cyan" />
          </div>
        ) : itemsList.length === 0 ? (
          <div className="card-cyber p-12 text-center">
            <Package className="h-14 w-14 text-gray-600 mx-auto mb-4" />
            <h3 className="font-display text-lg text-white mb-2">
              {activeTab === 'have' ? 'NO ITEMS YET' : 'WANT LIST IS EMPTY'}
            </h3>
            <p className="text-gray-400 text-sm mb-4">
              {activeTab === 'have'
                ? 'Browse products and components to add them to your collection.'
                : 'Browse products and components to add them to your want list.'}
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link to="/products" className="btn-cyber text-sm">
                BROWSE PRODUCTS
              </Link>
              <Link
                to="/components"
                className="border border-cyber-light/50 px-4 py-2 text-sm font-mono text-gray-400 hover:text-white hover:border-white transition-colors"
              >
                BROWSE COMPONENTS
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {itemsList.map((item: JunkbinItem) => {
              const isExpanded = expandedId === item.id;
              const edit = getEdit(item.id);
              const detailPath =
                item.content_type === 'product'
                  ? `/products/${item.object_id}`
                  : `/components/${item.object_id}/products`;

              return (
                <div
                  key={item.id}
                  className={clsx(
                    'card-cyber transition-all',
                    isExpanded && 'border-cyber-cyan/50'
                  )}
                >
                  {/* Card row */}
                  <div
                    className="p-4 flex items-center gap-4 cursor-pointer"
                    onClick={() => {
                      setExpandedId(isExpanded ? null : item.id);
                      setConfirmDelete(null);
                    }}
                  >
                    {/* Type icon */}
                    <div className="w-10 h-10 bg-cyber-dark border border-cyber-light/20 flex items-center justify-center flex-shrink-0">
                      {item.content_type === 'product' ? (
                        <Package className="h-5 w-5 text-cyber-cyan" />
                      ) : (
                        <Cpu className="h-5 w-5 text-cyber-pink" />
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <Link
                        to={detailPath}
                        onClick={(e) => e.stopPropagation()}
                        className="text-white hover:text-cyber-cyan font-semibold truncate block"
                      >
                        {item.item_name}
                      </Link>
                      <div className="text-xs text-gray-500 font-mono">
                        {item.item_manufacturer}
                      </div>
                    </div>

                    {/* Badges */}
                    <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
                      {activeTab === 'have' && (
                        <>
                          <span
                            className={clsx(
                              'badge-cyber text-[10px]',
                              item.status === 'available'
                                ? 'text-cyber-green border-cyber-green'
                                : 'text-gray-400 border-gray-600'
                            )}
                          >
                            {STATUS_LABELS[item.status]}
                          </span>
                          <span className="badge-cyber text-[10px] text-gray-400 border-gray-600">
                            {CONDITION_LABELS[item.condition]}
                          </span>
                        </>
                      )}
                      {item.quantity > 1 && (
                        <span className="text-xs text-gray-500 font-mono">
                          x{item.quantity}
                        </span>
                      )}
                      {item.visibility === 'private' ? (
                        <EyeOff className="h-3.5 w-3.5 text-gray-600" />
                      ) : (
                        <Eye className="h-3.5 w-3.5 text-gray-500" />
                      )}
                    </div>

                    {/* Expand icon */}
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4 text-gray-500 flex-shrink-0" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-gray-500 flex-shrink-0" />
                    )}
                  </div>

                  {/* Expanded edit section */}
                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-cyber-light/20 pt-4 space-y-4">
                      {activeTab === 'have' && (
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                              Status
                            </label>
                            <select
                              value={edit.status ?? item.status}
                              onChange={(e) =>
                                setEdit(item.id, { status: e.target.value as JunkbinItem['status'] })
                              }
                              className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                            >
                              <option value="not_for_trade">Not for Trade</option>
                              <option value="available">Available for Trade</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                              Condition
                            </label>
                            <select
                              value={edit.condition ?? item.condition}
                              onChange={(e) =>
                                setEdit(item.id, {
                                  condition: e.target.value as JunkbinItem['condition'],
                                })
                              }
                              className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                            >
                              <option value="new">New</option>
                              <option value="working">Working</option>
                              <option value="broken">Broken / For Parts</option>
                              <option value="unknown">Unknown</option>
                            </select>
                          </div>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                            Visibility
                          </label>
                          <select
                            value={edit.visibility ?? item.visibility}
                            onChange={(e) =>
                              setEdit(item.id, {
                                visibility: e.target.value as JunkbinItem['visibility'],
                              })
                            }
                            className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                          >
                            <option value="public">Public</option>
                            <option value="private">Private</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                            Quantity
                          </label>
                          <input
                            type="number"
                            min="1"
                            value={edit.quantity ?? item.quantity}
                            onChange={(e) =>
                              setEdit(item.id, { quantity: parseInt(e.target.value) || 1 })
                            }
                            className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                          Notes
                        </label>
                        <textarea
                          value={edit.notes ?? item.notes}
                          onChange={(e) => setEdit(item.id, { notes: e.target.value })}
                          maxLength={500}
                          rows={2}
                          className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-cyber-cyan focus:outline-none resize-none"
                        />
                      </div>

                      {/* Actions */}
                      <div className="flex items-center justify-between">
                        <div>
                          {confirmDelete === item.id ? (
                            <div className="flex items-center gap-3">
                              <span className="text-xs text-gray-400">Remove from junkbin?</span>
                              <button
                                onClick={() => deleteMutation.mutate(item.id)}
                                disabled={deleteMutation.isPending}
                                className="text-xs text-cyber-pink hover:text-white font-mono"
                              >
                                {deleteMutation.isPending ? 'REMOVING...' : 'YES, REMOVE'}
                              </button>
                              <button
                                onClick={() => setConfirmDelete(null)}
                                className="text-xs text-gray-500 hover:text-white font-mono"
                              >
                                CANCEL
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmDelete(item.id)}
                              className="flex items-center gap-1 text-xs text-gray-500 hover:text-cyber-pink transition-colors"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                              Remove
                            </button>
                          )}
                        </div>
                        <button
                          onClick={() => handleSave(item)}
                          disabled={updateMutation.isPending}
                          className="btn-cyber text-sm py-1.5 px-4"
                        >
                          {updateMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            'SAVE'
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
