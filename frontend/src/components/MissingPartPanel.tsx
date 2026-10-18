import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CheckCircle, ExternalLink, Loader2, Plus, Search, Send, Wrench } from 'lucide-react';
import { components, junkbin, productRequests } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import type { ExternalPart } from '../types';

// Same shape the backend accepts (external_search.looks_like_part_number)
const PART_NUMBER = /^[A-Z0-9][A-Z0-9\-./#+,]{2,38}[A-Z0-9#+]$/;

export function looksLikePartNumber(text: string): boolean {
  const q = text.replace(/\s+/g, '').toUpperCase();
  return PART_NUMBER.test(q) && /\d/.test(q) && /[A-Z]/.test(q);
}

/**
 * Shown when a component search finds nothing: asks DigiKey/Mouser for the part
 * (exact matches are added to the catalogue), then "what are you repairing?" -
 * create the product, ask a moderator to add it, or add the part to your wants.
 */
export default function MissingPartPanel({ query }: { query: string }) {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [settled, setSettled] = useState('');

  // wait until the search box has been still for a moment - each new search spends API quota
  useEffect(() => {
    const id = setTimeout(() => setSettled(query.trim()), 1200);
    return () => clearTimeout(id);
  }, [query]);

  const enabled = looksLikePartNumber(settled) && settled === query.trim();
  const { data, isFetching, error } = useQuery({
    queryKey: ['externalSearch', settled.toUpperCase()],
    queryFn: () => components.externalSearch(settled),
    enabled,
    staleTime: 60 * 60 * 1000,
    retry: false,
  });

  if (!looksLikePartNumber(query)) return null;
  if (!enabled || isFetching) {
    return (
      <div className="card-cyber p-6 mt-6 text-left flex items-center gap-3 text-gray-400 font-mono text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('missing_part.searching', { query: query.trim().toUpperCase() })}
      </div>
    );
  }
  if (error) {
    const statusCode = (error as any)?.response?.status;
    return (
      <div className="card-cyber p-6 mt-6 text-left text-gray-400 text-sm">
        {statusCode === 429 ? t('missing_part.rate_limited') : t('missing_part.unavailable')}
      </div>
    );
  }
  if (!data) return null;

  const part = data.added[0] || data.local_matches[0];
  const others = data.results.filter((r) => !data.added.some((a) => a.part_number === r.mpn && a.manufacturer === r.manufacturer));

  return (
    <div className="mt-6 space-y-4 text-left">
      {data.added.length > 0 ? (
        <div className="card-cyber p-5 border-cyber-green/40">
          <div className="flex items-center gap-2 text-cyber-green font-mono text-sm mb-2">
            <CheckCircle className="h-4 w-4" />
            {t('missing_part.added_title')}
          </div>
          {data.added.map((a) => (
            <Link key={a.id} to={`/components/${a.id}`} className="block text-white hover:text-cyber-cyan">
              {a.manufacturer} <span className="font-mono">{a.part_number}</span>
            </Link>
          ))}
          <p className="text-gray-500 text-xs mt-2">{t('missing_part.added_desc')}</p>
          {isAuthenticated && data.discovery_points_awarded > 0 && (
            <p className="text-cyber-yellow text-xs mt-1 font-mono">
              {t('missing_part.points_awarded', { count: data.discovery_points_awarded })}
            </p>
          )}
          {!isAuthenticated && data.pending_points > 0 && (
            <p className="text-xs mt-1">
              <Link to="/register" className="text-cyber-yellow hover:underline font-mono">
                {t('missing_part.points_pending', { count: data.pending_points, bonus: 5 })}
              </Link>
            </p>
          )}
        </div>
      ) : data.results.length === 0 ? (
        <div className="card-cyber p-5 text-gray-400 text-sm">{t('missing_part.not_found', { query: data.query })}</div>
      ) : null}

      {others.length > 0 && <DistributorResults query={data.query} results={others} canAdd={isAuthenticated} />}

      <RepairPrompt componentId={part?.id} partLabel={part ? `${part.manufacturer} ${part.part_number}` : data.query} query={data.query} />
    </div>
  );
}

function DistributorResults({ query, results, canAdd }: { query: string; results: ExternalPart[]; canAdd: boolean }) {
  const { t } = useTranslation();
  const [added, setAdded] = useState<Record<string, string>>({});
  const add = useMutation({
    mutationFn: (r: ExternalPart) => components.externalAdd({ query, mpn: r.mpn, manufacturer: r.manufacturer }),
    onSuccess: (res, r) => setAdded((prev) => ({ ...prev, [`${r.manufacturer}|${r.mpn}`]: res.id })),
  });

  return (
    <div className="card-cyber p-5">
      <div className="flex items-center gap-2 text-gray-300 font-mono text-sm mb-3">
        <Search className="h-4 w-4" />
        {t('missing_part.similar_title')}
      </div>
      <div className="divide-y divide-cyber-light/20">
        {results.map((r) => {
          const key = `${r.manufacturer}|${r.mpn}`;
          return (
            <div key={key} className="py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="font-mono text-white">{r.mpn}</span>
              <span className="text-gray-400">{r.manufacturer}</span>
              <span className="text-gray-500 flex-1 min-w-[12rem] truncate">{r.description}</span>
              {r.datasheet_url && (
                <a href={r.datasheet_url} target="_blank" rel="noopener noreferrer" className="text-cyber-cyan inline-flex items-center gap-1">
                  {t('missing_part.datasheet')} <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {added[key] ? (
                <Link to={`/components/${added[key]}`} className="text-cyber-green font-mono text-xs">{t('missing_part.view')}</Link>
              ) : canAdd ? (
                <button onClick={() => add.mutate(r)} disabled={add.isPending} className="btn-cyber text-xs py-1 inline-flex items-center gap-1">
                  <Plus className="h-3 w-3" /> {t('missing_part.add')}
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
      <p className="text-gray-600 text-xs mt-3">{t('missing_part.source_note')}</p>
    </div>
  );
}

function RepairPrompt({ componentId, partLabel, query }: { componentId?: string; partLabel: string; query: string }) {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [manufacturer, setManufacturer] = useState('');
  const [model, setModel] = useState('');
  const [notes, setNotes] = useState('');
  const [website, setWebsite] = useState('');      // spam trap, hidden from people

  const request = useMutation({
    mutationFn: () => productRequests.create({
      manufacturer, model_number: model, notes, component: componentId, search_query: query, website,
    }),
  });
  const want = useMutation({
    mutationFn: () => junkbin.create({ content_type: 'component', object_id: componentId!, item_type: 'want' }),
  });

  const ready = manufacturer.trim() && model.trim();
  const submitUrl = `/submit?manufacturer=${encodeURIComponent(manufacturer)}&model_number=${encodeURIComponent(model)}`;

  return (
    <div className="card-cyber p-5 border-cyber-cyan/40">
      <div className="flex items-center gap-2 text-cyber-cyan font-mono text-sm mb-1">
        <Wrench className="h-4 w-4" />
        {t('missing_part.repair_title')}
      </div>
      <p className="text-gray-500 text-xs mb-4">{t('missing_part.repair_desc', { part: partLabel })}</p>

      {request.isSuccess ? (
        <p className="text-cyber-green text-sm">{t('missing_part.request_sent')}</p>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 gap-3 mb-3">
            <input className="input-cyber" placeholder={t('missing_part.manufacturer_placeholder')}
              value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} maxLength={200} />
            <input className="input-cyber" placeholder={t('missing_part.model_placeholder')}
              value={model} onChange={(e) => setModel(e.target.value)} maxLength={200} />
          </div>
          <textarea className="input-cyber w-full mb-3" rows={2} placeholder={t('missing_part.notes_placeholder')}
            value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={2000} />
          <input type="text" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden"
            value={website} onChange={(e) => setWebsite(e.target.value)} name="website" />
          <div className="flex flex-wrap gap-2">
            <Link to={isAuthenticated ? submitUrl : '/register'}
              className={`btn-cyber text-sm inline-flex items-center gap-1 ${ready ? '' : 'pointer-events-none opacity-50'}`}>
              <Plus className="h-4 w-4" /> {t('missing_part.create_product')}
            </Link>
            <button onClick={() => request.mutate()} disabled={!ready || request.isPending}
              className="btn-cyber-pink text-sm inline-flex items-center gap-1 disabled:opacity-50">
              <Send className="h-4 w-4" /> {t('missing_part.ask_moderator')}
            </button>
          </div>
          {request.isError && <p className="text-cyber-pink text-xs mt-2">{t('missing_part.request_failed')}</p>}
        </>
      )}

      {componentId && <div className="border-t border-cyber-light/20 mt-4 pt-3 text-sm">
        {isAuthenticated ? (
          want.isSuccess ? (
            <span className="text-cyber-green">{t('missing_part.want_added')}</span>
          ) : (
            <button onClick={() => want.mutate()} disabled={want.isPending} className="text-cyber-cyan hover:underline">
              {t('missing_part.add_want')}
            </button>
          )
        ) : (
          <Link to="/register" className="text-cyber-cyan hover:underline">{t('missing_part.signup_for_wants')}</Link>
        )}
      </div>}
    </div>
  );
}
