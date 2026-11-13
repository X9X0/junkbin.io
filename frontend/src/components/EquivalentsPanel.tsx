import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Clock, ExternalLink, Package, Plus, RefreshCw, Search } from 'lucide-react';
import { components } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import type { Dealer, EquivalentParts, ExternalPart, Substitute } from '../types';

interface Props {
  componentId: string;
  componentType: string;
  mode: 'equivalents' | 'not_stocked';
  equivalents?: EquivalentParts | null;
  /** curated stand-ins (valves): shown instead of a distributor search */
  substitutes?: Substitute[];
  madeTodayBy?: string[];
  /** specialist shops, for parts no distributor stocks */
  dealers?: Dealer[];
}

const NOT_STOCKED_KEY: Record<string, string> = {
  vacuum_tube: 'equivalents.not_stocked_tubes',
  transformer: 'equivalents.not_stocked_transformers',
  speaker: 'equivalents.not_stocked_speakers',
};

const GRADE_STYLE: Record<Substitute['grade'], string> = {
  same: 'text-cyber-green border-cyber-green/40',
  near: 'text-cyber-cyan border-cyber-cyan/40',
  check: 'text-cyber-yellow border-cyber-yellow/40',
};

/**
 * What else fits a valve socket, from the substitution table (backend valves.py). No
 * distributor the site asks stocks valves, so this is the whole answer for them: the same
 * valve under its other names, drop-ins with a difference, and the ones that fit but need
 * the bias or ratings checked first.
 */
function SubstitutesTable({ substitutes, madeTodayBy }: { substitutes: Substitute[]; madeTodayBy: string[] }) {
  const { t } = useTranslation();
  return (
    <>
      {madeTodayBy.length > 0 && (
        <p className="text-gray-400 text-sm mb-3">{t('equivalents.made_today', { makers: madeTodayBy.join(', ') })}</p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-cyber-light/10 text-gray-500 font-mono text-xs uppercase">
              <th className="py-2 pr-4 text-left">Part</th>
              <th className="py-2 pr-4 text-left">{t('equivalents.fit')}</th>
              <th className="py-2 text-left">{t('equivalents.notes')}</th>
            </tr>
          </thead>
          <tbody>
            {substitutes.map((s) => (
              <tr key={s.id} className="border-b border-cyber-light/5 hover:bg-cyber-light/5 align-top">
                <td className="py-2.5 pr-4 whitespace-nowrap">
                  <Link to={`/components/${s.id}`} className="text-white font-mono hover:text-cyber-cyan">{s.part_number}</Link>
                  {s.made_today && <span className="ml-2 text-cyber-green text-xs" title={t('equivalents.in_production')}>●</span>}
                  {s.usage_count > 0 && (
                    <div className="text-gray-500 text-xs">{t('equivalents.used_in', { count: s.usage_count })}</div>
                  )}
                </td>
                <td className="py-2.5 pr-4 whitespace-nowrap">
                  <span className={`badge-cyber text-xs ${GRADE_STYLE[s.grade]}`}>{t(`equivalents.grade_${s.grade}`)}</span>
                </td>
                <td className="py-2.5 text-gray-400">{s.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-gray-600 text-xs mt-3">{t('equivalents.substitutes_note')}</p>
    </>
  );
}

function isStale(isoDate: string): boolean {
  return Date.now() - new Date(isoDate).getTime() > 7 * 24 * 3600 * 1000;
}

function timeAgo(isoDate: string): string {
  const days = Math.floor((Date.now() - new Date(isoDate).getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 month ago' : `${months} months ago`;
}

/**
 * The "pricing" card for a generic parts-list line ("CAP 10nF 200V") or a part no
 * distributor stocks. A generic line has no maker's part number to price, so the
 * Lookup button asks DigiKey for parts that fit its value and ratings instead
 * (backend parametric.py) and lists them with stock, price and an add button.
 */
export default function EquivalentsPanel({ componentId, componentType, mode, equivalents, substitutes = [], madeTodayBy = [], dealers = [] }: Props) {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<Record<string, string>>({});

  const lookup = useMutation({
    mutationFn: () => components.lookup(componentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['component', componentId] });
      setError(null);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      setError(err.response?.data?.detail || t('missing_part.unavailable')),
  });
  const add = useMutation({
    mutationFn: (r: ExternalPart) => components.externalAdd({ query: equivalents!.query, mpn: r.mpn, manufacturer: r.manufacturer }),
    onSuccess: (res, r) => setAdded((prev) => ({ ...prev, [`${r.manufacturer}|${r.mpn}`]: res.id })),
  });

  if (mode === 'not_stocked') {
    return (
      <div className="card-cyber p-6">
        <h2 className="font-display text-lg font-bold text-white flex items-center gap-2 mb-3">
          <Search className="h-5 w-5 text-cyber-green" />
          {t('equivalents.title')}
        </h2>
        {substitutes.length > 0 ? (
          <SubstitutesTable substitutes={substitutes} madeTodayBy={madeTodayBy} />
        ) : (
          <p className="text-gray-500 text-sm">
            {t('equivalents.not_stocked', { what: t(NOT_STOCKED_KEY[componentType] || 'equivalents.not_stocked_tubes') })}
            {componentType === 'vacuum_tube' && ` ${t('equivalents.none_curated')}`}
          </p>
        )}
        {dealers.length > 0 && (
          <p className="text-gray-500 text-xs mt-4 leading-relaxed">
            <span className="font-mono uppercase text-gray-600 mr-2">{t('equivalents.dealers')}</span>
            {dealers.map((d, i) => (
              <span key={d.url}>
                {i > 0 && <span className="text-gray-700"> · </span>}
                <a href={d.url} target="_blank" rel="noopener noreferrer" className="text-cyber-cyan hover:text-white">
                  {d.name}
                </a>
                <span className="text-gray-600"> ({d.region})</span>
              </span>
            ))}
          </p>
        )}
      </div>
    );
  }

  const stale = equivalents?.last_updated ? isStale(equivalents.last_updated) : false;
  const candidates = equivalents?.candidates ?? [];

  return (
    <div className="card-cyber p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-lg font-bold text-white flex items-center gap-2">
          <Search className="h-5 w-5 text-cyber-green" />
          {t('equivalents.title')}
        </h2>
        <div className="flex items-center gap-3">
          {equivalents?.last_updated && (
            <span className={`text-xs font-mono flex items-center gap-1 ${stale ? 'text-yellow-500' : 'text-gray-500'}`}>
              <Clock className="h-3 w-3" />
              {stale && <AlertTriangle className="h-3 w-3" />}
              {t('equivalents.updated', { when: timeAgo(equivalents.last_updated) })}
            </span>
          )}
          {isAuthenticated && (
            <button
              onClick={() => lookup.mutate()}
              disabled={lookup.isPending}
              className="btn-cyber text-xs px-3 py-1 flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${lookup.isPending ? 'animate-spin' : ''}`} />
              {equivalents ? t('equivalents.refresh') : t('equivalents.find')}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 border border-red-500/30 bg-red-500/5 text-red-400 text-sm font-mono">{error}</div>
      )}

      {lookup.isPending && !equivalents && (
        <div className="py-8 text-center text-cyber-cyan font-mono animate-pulse text-sm">
          {t('equivalents.searching')}
        </div>
      )}

      {!equivalents && !lookup.isPending && (
        <div className="py-8 text-center">
          <Package className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm mb-3">{t('equivalents.empty_title')}</p>
          <p className="text-gray-600 text-xs max-w-md mx-auto">
            {isAuthenticated ? t('equivalents.empty_desc') : t('equivalents.empty_login')}
          </p>
        </div>
      )}

      {equivalents && candidates.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-4">{t('equivalents.none_found', { query: equivalents.query })}</p>
      )}

      {candidates.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-cyber-light/10 text-gray-500 font-mono text-xs uppercase">
                <th className="py-2 pr-4 text-left">Part</th>
                <th className="py-2 pr-4 text-right">{t('equivalents.stock')}</th>
                <th className="py-2 pr-4 text-right">{t('equivalents.price')}</th>
                <th className="py-2 text-right"></th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => {
                const key = `${c.manufacturer}|${c.mpn}`;
                const offers = c.sellers.flatMap((s) => s.offers);
                const best = offers.reduce<typeof offers[number] | null>((b, o) => (!b || o.price < b.price ? o : b), null);
                const url = best?.buy_url || c.product_url;
                return (
                  <tr key={key} className="border-b border-cyber-light/5 hover:bg-cyber-light/5 align-top">
                    <td className="py-2.5 pr-4">
                      <div className="text-white font-mono">{c.mpn}</div>
                      <div className="text-gray-400 text-xs">{c.manufacturer}</div>
                      <div className="text-gray-500 text-xs">{c.description}</div>
                      {(c.fit.notes.length > 0 || c.fit.value === 'unknown') && (
                        <div className="text-cyber-yellow/80 text-xs font-mono mt-0.5">
                          {[...c.fit.notes, ...(c.fit.value === 'unknown' ? [t('equivalents.value_unknown')] : [])].join(' · ')}
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono whitespace-nowrap">
                      {(c.stock ?? 0) > 0 ? <span className="text-cyber-green">{(c.stock ?? 0).toLocaleString()}</span> : <span className="text-gray-600">-</span>}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono text-cyber-yellow whitespace-nowrap">
                      {best ? (
                        <>
                          {best.currency === 'USD' ? '$' : best.currency + ' '}{best.price.toFixed(4)}
                          {best.qty_min > 1 && <span className="text-gray-600 text-xs ml-1">@{best.qty_min}+</span>}
                        </>
                      ) : <span className="text-gray-600">-</span>}
                    </td>
                    <td className="py-2.5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        {c.datasheet_url && (
                          <a href={c.datasheet_url} target="_blank" rel="noopener noreferrer" className="text-cyber-cyan" title={t('equivalents.datasheet')}>
                            <ExternalLink className="h-3.5 w-3.5 inline" />
                          </a>
                        )}
                        {url && (
                          <a href={url} target="_blank" rel="noopener noreferrer" className="text-cyber-pink hover:text-white transition-colors" title={c.sources.join(', ')}>
                            <ExternalLink className="h-3.5 w-3.5 inline" />
                          </a>
                        )}
                        {added[key] ? (
                          <Link to={`/components/${added[key]}`} className="text-cyber-green font-mono text-xs">{t('equivalents.view')}</Link>
                        ) : isAuthenticated ? (
                          <button onClick={() => add.mutate(c)} disabled={add.isPending} className="btn-cyber text-xs py-1 inline-flex items-center gap-1" title={t('equivalents.add')}>
                            <Plus className="h-3 w-3" />
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {equivalents && (
        <p className="text-gray-600 text-xs mt-3">
          {equivalents.family_of
            ? t('equivalents.family_note', { part: equivalents.family_of, stem: equivalents.query })
            : t('equivalents.query_note', { query: equivalents.query })}
        </p>
      )}
    </div>
  );
}
