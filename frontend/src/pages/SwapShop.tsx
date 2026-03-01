import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { junkbin } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { Store, Package, Cpu, Search, MessageSquare } from 'lucide-react';
import clsx from 'clsx';
import Pagination from '../components/Pagination';
import type { JunkbinItem } from '../types';

const CONDITION_LABELS: Record<string, string> = {
  new: 'New',
  working: 'Working',
  broken: 'Broken',
  unknown: 'Unknown',
};

function SwapCard({
  item,
  tab,
  isAuthenticated,
  currentUserId,
}: {
  item: JunkbinItem;
  tab: 'have' | 'want';
  isAuthenticated: boolean;
  currentUserId?: string;
}) {
  const isOwnItem = currentUserId === item.user.id;
  const canContact =
    isAuthenticated && !isOwnItem && tab === 'have' && item.status === 'available';
  const detailPath =
    item.content_type === 'product'
      ? `/products/${item.object_id}`
      : `/components/${item.object_id}/products`;

  return (
    <div className="card-cyber p-4 flex flex-col gap-3">
      {/* Top row: type badge + status */}
      <div className="flex items-start justify-between gap-2">
        <span
          className={clsx(
            'badge-cyber text-[10px]',
            item.content_type === 'product'
              ? 'text-cyber-cyan border-cyber-cyan'
              : 'text-cyber-pink border-cyber-pink'
          )}
        >
          {item.content_type === 'product' ? (
            <><Package className="h-3 w-3 inline mr-1" />PRODUCT</>
          ) : (
            <><Cpu className="h-3 w-3 inline mr-1" />COMPONENT</>
          )}
        </span>
        {tab === 'have' && (
          <span
            className={clsx(
              'badge-cyber text-[10px] flex-shrink-0',
              item.status === 'available'
                ? 'text-cyber-green border-cyber-green'
                : 'text-gray-500 border-gray-600'
            )}
          >
            {item.status === 'available' ? 'AVAILABLE' : 'NOT FOR TRADE'}
          </span>
        )}
      </div>

      {/* Item name */}
      <div>
        <Link
          to={detailPath}
          className="font-semibold text-white hover:text-cyber-cyan transition-colors block leading-tight"
        >
          {item.item_name}
        </Link>
        <div className="text-xs text-gray-500 font-mono mt-0.5">{item.item_manufacturer}</div>
      </div>

      {/* Condition + quantity row */}
      <div className="flex flex-wrap items-center gap-2">
        {tab === 'have' && (
          <span className="badge-cyber text-[10px] text-gray-400 border-gray-600">
            {CONDITION_LABELS[item.condition] || item.condition}
          </span>
        )}
        {item.quantity > 1 && (
          <span className="text-xs text-gray-500 font-mono">×{item.quantity}</span>
        )}
      </div>

      {/* Notes */}
      {item.notes && (
        <p className="text-sm text-gray-400 line-clamp-2 flex-1">{item.notes}</p>
      )}

      {/* Footer: user + contact */}
      <div className="flex items-center justify-between pt-2 border-t border-cyber-light/20 mt-auto">
        <Link
          to={`/users/${item.user.id}`}
          className="flex items-center gap-2 group min-w-0"
        >
          <div className="w-6 h-6 rounded-full bg-cyber-gray border border-cyber-light/30 flex items-center justify-center overflow-hidden flex-shrink-0">
            {item.user.avatar ? (
              <img src={item.user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              <span className="text-gray-500 font-mono text-[10px]">
                {item.user.username.charAt(0).toUpperCase()}
              </span>
            )}
          </div>
          <span className="text-xs text-gray-400 group-hover:text-cyber-cyan transition-colors font-mono truncate">
            {item.user.display_name || item.user.username}
          </span>
        </Link>
        {canContact && (
          <Link
            to={`/messages/new?user=${item.user.id}`}
            className="flex items-center gap-1 text-xs text-cyber-cyan hover:text-white transition-colors font-mono flex-shrink-0 ml-2"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            CONTACT
          </Link>
        )}
      </div>
    </div>
  );
}

export default function SwapShop() {
  const { isAuthenticated, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<'have' | 'want'>('have');
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [contentType, setContentType] = useState('');
  const [availableOnly, setAvailableOnly] = useState(false);
  const page = parseInt(searchParams.get('page') || '1', 10);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const { data, isLoading } = useQuery({
    queryKey: ['swapshop', activeTab, debouncedSearch, contentType, availableOnly, page],
    queryFn: () =>
      junkbin.list({
        item_type: activeTab,
        ...(debouncedSearch && { q: debouncedSearch }),
        ...(contentType && { content_type: contentType }),
        ...(availableOnly && activeTab === 'have' && { status: 'available' }),
        page,
      }),
  });

  const totalPages = data ? Math.ceil(data.count / 20) : 0;

  const resetPage = () => {
    const p = new URLSearchParams(searchParams);
    p.delete('page');
    setSearchParams(p);
  };

  const handlePageChange = (newPage: number) => {
    const p = new URLSearchParams(searchParams);
    if (newPage > 1) {
      p.set('page', String(newPage));
    } else {
      p.delete('page');
    }
    setSearchParams(p);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-2">
        <div className="flex items-center gap-3">
          <Store className="h-7 w-7 text-cyber-cyan" />
          <h1 className="font-display text-2xl md:text-3xl font-bold text-white">
            SWAP <span className="text-cyber-cyan">SHOP</span>
          </h1>
        </div>
        {isAuthenticated && (
          <Link to="/my-junkbin" className="btn-cyber text-sm py-1.5 whitespace-nowrap">
            MY JUNKBIN →
          </Link>
        )}
      </div>
      <p className="text-gray-500 font-mono text-sm mb-8">
        // Browse items the community has for trade or is looking for
      </p>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-cyber-light/30 mb-6">
        {(['have', 'want'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              setAvailableOnly(false);
              resetPage();
            }}
            className={clsx(
              'py-3 px-6 font-mono text-sm border-b-2 transition-colors',
              activeTab === tab
                ? tab === 'have'
                  ? 'border-cyber-cyan text-cyber-cyan'
                  : 'border-cyber-yellow text-cyber-yellow'
                : 'border-transparent text-gray-500 hover:text-white'
            )}
          >
            {tab === 'have' ? 'HAVE' : 'WANT'}
          </button>
        ))}
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              resetPage();
            }}
            placeholder="Search by name or manufacturer..."
            className="w-full bg-cyber-dark border border-cyber-light/50 px-4 py-2 pl-10 text-sm font-mono text-gray-200 placeholder-gray-500 focus:border-cyber-cyan focus:outline-none"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
        </div>
        <select
          value={contentType}
          onChange={(e) => {
            setContentType(e.target.value);
            resetPage();
          }}
          className="bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white font-mono focus:border-cyber-cyan focus:outline-none"
        >
          <option value="">All Types</option>
          <option value="product">Products</option>
          <option value="component">Components</option>
        </select>
        {activeTab === 'have' && (
          <label className="flex items-center gap-2 text-sm font-mono text-gray-400 cursor-pointer whitespace-nowrap">
            <input
              type="checkbox"
              checked={availableOnly}
              onChange={(e) => {
                setAvailableOnly(e.target.checked);
                resetPage();
              }}
              className="w-4 h-4 accent-cyber-cyan"
            />
            Available Only
          </label>
        )}
      </div>

      {/* Result count */}
      {!isLoading && data && (
        <p className="text-gray-500 font-mono text-xs mb-4">
          {data.count} {data.count === 1 ? 'item' : 'items'} found
        </p>
      )}

      {/* Results grid */}
      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-44 bg-cyber-gray/50 border border-cyber-light/10 animate-pulse" />
          ))}
        </div>
      ) : data?.results?.length ? (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.results.map((item) => (
              <SwapCard
                key={item.id}
                item={item}
                tab={activeTab}
                isAuthenticated={isAuthenticated}
                currentUserId={user?.id}
              />
            ))}
          </div>
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            color="cyan"
            className="mt-8"
          />
        </>
      ) : (
        <div className="text-center py-16 card-cyber">
          <Store className="h-12 w-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 font-mono">
            {activeTab === 'have'
              ? 'No items for trade yet.'
              : 'Nobody is looking for anything yet.'}
          </p>
          {!isAuthenticated && (
            <Link to="/login" className="text-cyber-cyan hover:underline text-sm mt-2 inline-block font-mono">
              Log in to add your items
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
