import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { components } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import type { NexarData } from '../types';
import {
  DollarSign,
  RefreshCw,
  ExternalLink,
  FileText,
  Clock,
  Package,
  AlertTriangle,
} from 'lucide-react';

interface PricingPanelProps {
  componentId: string;
  pricingData?: NexarData | null;
  datasheetUrl?: string;
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 month ago' : `${months} months ago`;
}

function isStale(isoDate: string): boolean {
  const diff = Date.now() - new Date(isoDate).getTime();
  return diff > 7 * 24 * 60 * 60 * 1000; // 7 days
}

export default function PricingPanel({ componentId, pricingData, datasheetUrl }: PricingPanelProps) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const lookupMutation = useMutation({
    mutationFn: () => components.lookup(componentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['component', componentId] });
      setError(null);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || 'Lookup failed. Try again later.';
      setError(msg);
    },
  });

  const stale = pricingData?.last_updated ? isStale(pricingData.last_updated) : false;

  return (
    <div className="card-cyber p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-lg font-bold text-white flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-cyber-green" />
          PRICING & AVAILABILITY
        </h2>

        <div className="flex items-center gap-3">
          {pricingData?.last_updated && (
            <span className={`text-xs font-mono flex items-center gap-1 ${stale ? 'text-yellow-500' : 'text-gray-500'}`}>
              <Clock className="h-3 w-3" />
              {stale && <AlertTriangle className="h-3 w-3" />}
              Updated {timeAgo(pricingData.last_updated)}
            </span>
          )}

          {isAuthenticated && (
            <button
              onClick={() => lookupMutation.mutate()}
              disabled={lookupMutation.isPending}
              className="btn-cyber text-xs px-3 py-1 flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${lookupMutation.isPending ? 'animate-spin' : ''}`} />
              {pricingData ? 'Refresh' : 'Lookup Pricing'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 border border-red-500/30 bg-red-500/5 text-red-400 text-sm font-mono">
          {error}
        </div>
      )}

      {lookupMutation.isPending && !pricingData && (
        <div className="py-8 text-center">
          <div className="text-cyber-cyan font-mono animate-pulse text-sm">
            QUERYING DISTRIBUTORS...
          </div>
        </div>
      )}

      {!pricingData && !lookupMutation.isPending && (
        <div className="py-8 text-center">
          <Package className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm mb-3">
            No pricing data yet.
          </p>
          {isAuthenticated ? (
            <p className="text-gray-600 text-xs">
              Click "Lookup Pricing" to fetch live data from distributors.
            </p>
          ) : (
            <p className="text-gray-600 text-xs">
              Log in to look up pricing and availability.
            </p>
          )}
        </div>
      )}

      {pricingData && (
        <>
          {/* Datasheet link */}
          {(pricingData.datasheet_url || datasheetUrl) && (
            <a
              href={pricingData.datasheet_url || datasheetUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 p-3 mb-4 border border-cyber-cyan/20 bg-cyber-cyan/5
                         text-cyber-cyan hover:bg-cyber-cyan/10 transition-colors"
            >
              <FileText className="h-4 w-4 flex-shrink-0" />
              <span className="text-sm font-mono">View Datasheet</span>
              <ExternalLink className="h-3 w-3 ml-auto flex-shrink-0" />
            </a>
          )}

          {/* Seller table */}
          {pricingData.sellers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-cyber-light/10 text-gray-500 font-mono text-xs uppercase">
                    <th className="py-2 pr-4 text-left">Distributor</th>
                    <th className="py-2 pr-4 text-right">Stock</th>
                    <th className="py-2 pr-4 text-right">Unit Price</th>
                    <th className="py-2 text-right">Buy</th>
                  </tr>
                </thead>
                <tbody>
                  {pricingData.sellers.map((seller, i) => {
                    const bestOffer = seller.offers.reduce(
                      (best, o) => (!best || o.price < best.price ? o : best),
                      seller.offers[0]
                    );
                    const totalStock = seller.offers.reduce((sum, o) => sum + (o.stock || 0), 0);

                    return (
                      <tr key={i} className="border-b border-cyber-light/5 hover:bg-cyber-light/5">
                        <td className="py-2.5 pr-4 text-white font-medium">{seller.name}</td>
                        <td className="py-2.5 pr-4 text-right font-mono">
                          {totalStock > 0 ? (
                            <span className="text-cyber-green">{totalStock.toLocaleString()}</span>
                          ) : (
                            <span className="text-gray-600">-</span>
                          )}
                        </td>
                        <td className="py-2.5 pr-4 text-right font-mono text-cyber-yellow">
                          {bestOffer.currency === 'USD' ? '$' : bestOffer.currency + ' '}
                          {bestOffer.price.toFixed(4)}
                          {bestOffer.qty_min > 1 && (
                            <span className="text-gray-600 text-xs ml-1">
                              @{bestOffer.qty_min}+
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 text-right">
                          {bestOffer.buy_url ? (
                            <a
                              href={bestOffer.buy_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-cyber-pink hover:text-white transition-colors"
                            >
                              <ExternalLink className="h-3.5 w-3.5 inline" />
                            </a>
                          ) : (
                            <span className="text-gray-600">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm text-center py-4">
              No distributor listings found.
            </p>
          )}

          {/* Specs summary */}
          {pricingData.specs.length > 0 && (
            <details className="mt-4">
              <summary className="text-xs font-mono text-gray-500 cursor-pointer hover:text-gray-400">
                Technical Specs ({pricingData.specs.length})
              </summary>
              <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                {pricingData.specs.slice(0, 20).map((spec, i) => (
                  <div key={i} className="flex justify-between py-0.5 border-b border-cyber-light/5">
                    <span className="text-gray-500 truncate mr-2">{spec.name}</span>
                    <span className="text-gray-300 font-mono text-right">{spec.value}</span>
                  </div>
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}
