import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Loader2, Wrench, X } from 'lucide-react';
import { productRequests } from '../api/endpoints';
import { PRODUCT_CATEGORIES } from '../utils/constants';
import type { ProductRequest } from '../types';

/**
 * Moderation: "I need this part for <product>" requests filed after a component
 * search. Create the product (the requested part is linked to it) or dismiss.
 */
export default function ProductRequestsPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['pendingProductRequests'],
    queryFn: () => productRequests.list({ status: 'pending', page_size: 100 }),
  });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['pendingProductRequests'] });
    queryClient.invalidateQueries({ queryKey: ['pendingCounts'] });
  };

  if (isLoading) {
    return <div className="card-cyber p-4 mb-6 text-gray-500 font-mono text-sm"><Loader2 className="h-4 w-4 animate-spin inline mr-2" />PRODUCT REQUESTS</div>;
  }
  const items = data?.results || [];
  if (!items.length) return null;

  return (
    <div className="card-cyber p-4 mb-6">
      <div className="flex items-center gap-2 font-mono text-sm text-cyber-cyan mb-3">
        <Wrench className="h-4 w-4" /> PRODUCT REQUESTS ({items.length})
      </div>
      <div className="divide-y divide-cyber-light/20">
        {items.map((r) => <RequestRow key={r.id} request={r} onDone={refresh} />)}
      </div>
    </div>
  );
}

function RequestRow({ request, onDone }: { request: ProductRequest; onDone: () => void }) {
  const [category, setCategory] = useState('other');
  const fulfil = useMutation({ mutationFn: () => productRequests.fulfil(request.id, category), onSuccess: onDone });
  const dismiss = useMutation({ mutationFn: () => productRequests.dismiss(request.id), onSuccess: onDone });
  const busy = fulfil.isPending || dismiss.isPending;

  return (
    <div className="py-3 flex flex-wrap items-center gap-3 text-sm">
      <div className="flex-1 min-w-[16rem]">
        <div className="text-white">{request.manufacturer} <span className="font-mono">{request.model_number}</span></div>
        <div className="text-gray-500 text-xs">
          needs{' '}
          {request.component ? (
            <Link to={`/components/${request.component.id}`} className="text-cyber-cyan hover:underline">
              {request.component.manufacturer} {request.component.part_number}
            </Link>
          ) : request.search_query || 'a part'}
          {' · '}{request.requested_by?.username || 'visitor'}
          {' · '}{new Date(request.created_at).toLocaleDateString()}
        </div>
        {request.notes && <div className="text-gray-400 text-xs mt-1">{request.notes}</div>}
      </div>
      <select className="input-cyber text-xs py-1 w-44" value={category} onChange={(e) => setCategory(e.target.value)}>
        {PRODUCT_CATEGORIES.filter((c) => c.value).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      <button onClick={() => fulfil.mutate()} disabled={busy} className="btn-cyber-green text-xs py-1 inline-flex items-center gap-1">
        <Check className="h-3 w-3" /> Create product
      </button>
      <button onClick={() => dismiss.mutate()} disabled={busy} className="btn-cyber-pink text-xs py-1 inline-flex items-center gap-1">
        <X className="h-3 w-3" /> Dismiss
      </button>
    </div>
  );
}
