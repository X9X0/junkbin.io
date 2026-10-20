import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ExternalLink, Flag, Loader2, ShieldCheck } from 'lucide-react';
import { importReview, type ImportBatch, type ImportReviewItem } from '../../api/endpoints';

/**
 * Review random samples of each bulk-import batch, then approve the batch.
 * A batch can be approved once enough items are marked correct and none is flagged.
 */
export default function ImportReviewPanel() {
  const queryClient = useQueryClient();
  const { data: batches, isLoading } = useQuery({ queryKey: ['importBatches'], queryFn: importReview.batches });
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [showFlagged, setShowFlagged] = useState<string | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['importBatches'] });

  if (isLoading) return <div className="card-cyber p-6 text-gray-500 font-mono text-sm"><Loader2 className="h-4 w-4 animate-spin inline mr-2" />Loading batches</div>;

  if (reviewing) {
    const batch = batches?.find((b) => b.batch === reviewing);
    return <ReviewSession batch={batch!} onExit={() => { setReviewing(null); refresh(); }} onVerdict={refresh} />;
  }

  return (
    <div className="space-y-4">
      <div className="card-cyber p-4 text-sm text-gray-400">
        Each batch is content a bulk import created. Review randomly drawn items against their evidence; a batch
        can be approved once {batches?.[0]?.target ?? 100} items (or the whole batch, if smaller) are marked correct
        and nothing is flagged. Flags tell us which rule to fix before trying again.
      </div>
      {batches?.map((b) => (
        <BatchRow key={b.batch} batch={b} onReview={() => setReviewing(b.batch)}
          onFlagged={() => setShowFlagged(showFlagged === b.batch ? null : b.batch)}
          flaggedOpen={showFlagged === b.batch} onApproved={refresh} />
      ))}
    </div>
  );
}

function BatchRow({ batch, onReview, onFlagged, flaggedOpen, onApproved }: {
  batch: ImportBatch; onReview: () => void; onFlagged: () => void; flaggedOpen: boolean; onApproved: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const approve = useMutation({ mutationFn: () => importReview.approve(batch.batch), onSuccess: onApproved });
  const pct = batch.target ? Math.min(100, Math.round((batch.correct / batch.target) * 100)) : 0;

  return (
    <div className="card-cyber p-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[16rem]">
          <div className="text-white">{batch.label}</div>
          <div className="text-xs text-gray-500 font-mono">
            {batch.batch} · {batch.total} items · {batch.unapproved} not yet public
          </div>
          <div className="mt-2 h-1.5 bg-cyber-light/20 w-full max-w-md">
            <div className={`h-1.5 ${batch.flagged ? 'bg-cyber-pink' : 'bg-cyber-green'}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="text-xs text-gray-500 font-mono mt-1">
            {batch.correct}/{batch.target} correct
            {batch.flagged > 0 && <span className="text-cyber-pink"> · {batch.flagged} flagged</span>}
          </div>
        </div>
        <button onClick={onReview} className="btn-cyber text-sm" disabled={batch.reviewed >= batch.total}>Review</button>
        {batch.flagged > 0 && (
          <button onClick={onFlagged} className="btn-cyber-pink text-sm inline-flex items-center gap-1">
            <Flag className="h-3 w-3" /> Flagged ({batch.flagged})
          </button>
        )}
        {batch.unapproved > 0 && (
          confirming ? (
            <button onClick={() => approve.mutate()} disabled={approve.isPending}
              className="btn-cyber-green text-sm inline-flex items-center gap-1">
              <ShieldCheck className="h-4 w-4" /> Confirm: publish {batch.unapproved}
            </button>
          ) : (
            <button onClick={() => setConfirming(true)} disabled={!batch.can_approve}
              className="btn-cyber-green text-sm inline-flex items-center gap-1 disabled:opacity-40"
              title={batch.can_approve ? '' : 'Needs more correct reviews and no open flags'}>
              <ShieldCheck className="h-4 w-4" /> Approve batch
            </button>
          )
        )}
      </div>
      {approve.isError && <div className="text-cyber-pink text-xs mt-2">{(approve.error as any)?.response?.data?.detail || 'Approval failed.'}</div>}
      {approve.isSuccess && <div className="text-cyber-green text-xs mt-2 font-mono">Published: {JSON.stringify(approve.data)}</div>}
      {flaggedOpen && <FlaggedList batch={batch.batch} />}
    </div>
  );
}

function FlaggedList({ batch }: { batch: string }) {
  const { data, isLoading } = useQuery({ queryKey: ['importFlagged', batch], queryFn: () => importReview.flagged(batch) });
  if (isLoading) return <div className="text-gray-500 text-xs mt-3">Loading…</div>;
  return (
    <div className="mt-3 divide-y divide-cyber-light/20 text-sm">
      {data?.map((item) => (
        <div key={item.id} className="py-2">
          <ItemLink item={item} /> <span className="text-gray-500 text-xs">— {item.reviewer}</span>
          <div className="text-cyber-pink text-xs">{item.note || '(no note)'}</div>
        </div>
      ))}
    </div>
  );
}

function ItemLink({ item }: { item: ImportReviewItem }) {
  const to = item.item_type === 'product' || item.item_type === 'firmware' ? `/products/${item.slug || item.id}`
    : `/components/${item.item_type === 'component' ? item.id : item.component_id}`;
  return (
    <Link to={to} target="_blank" className="text-white hover:text-cyber-cyan">
      {item.title}{item.revision ? ` · Rev ${item.revision}` : ''}
    </Link>
  );
}

function ReviewSession({ batch, onExit, onVerdict }: { batch: ImportBatch; onExit: () => void; onVerdict: () => void }) {
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [note, setNote] = useState('');
  const [done, setDone] = useState(0);
  const { data: queue, isFetching } = useQuery({
    queryKey: ['importNext', batch.batch],
    queryFn: () => importReview.next(batch.batch, 10),
    refetchOnWindowFocus: false,
  });
  const item = queue?.[index];
  const verdict = useMutation({
    mutationFn: (v: 'correct' | 'flagged') => importReview.verdict({ batch: batch.batch, object_id: item!.id, verdict: v, note }),
    onSuccess: () => {
      setNote('');
      setDone((d) => d + 1);
      onVerdict();
      if (queue && index + 1 < queue.length) setIndex(index + 1);
      else { setIndex(0); queryClient.invalidateQueries({ queryKey: ['importNext', batch.batch] }); }
    },
  });

  return (
    <div className="card-cyber p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-white">{batch.label}</div>
          <div className="text-xs text-gray-500 font-mono">{batch.correct + done}/{batch.target} reviewed toward approval · {done} this session</div>
        </div>
        <button onClick={onExit} className="btn-cyber text-sm">Done</button>
      </div>

      {isFetching && !item ? (
        <div className="text-gray-500 text-sm"><Loader2 className="h-4 w-4 animate-spin inline mr-2" />Drawing items…</div>
      ) : !item ? (
        <div className="text-cyber-green text-sm">Every item in this batch has been reviewed.</div>
      ) : (
        <div className="grid md:grid-cols-[1fr_18rem] gap-5">
          <div className="min-w-0">
            <div className="text-xl text-white mb-1"><ItemLink item={item} /></div>
            <div className="text-xs text-gray-500 font-mono mb-3">
              {[item.category, item.subcategory, item.year, item.component_count ? `${item.component_count} BOM rows` : null]
                .filter(Boolean).join(' · ')}
            </div>
            {item.description && <p className="text-gray-300 text-sm mb-3">{item.description}</p>}
            <div className="space-y-1 mb-3">
              {item.documents.map((d) => (
                <a key={d.url} href={d.url} target="_blank" rel="noopener noreferrer"
                  className="flex items-start gap-2 text-sm text-cyber-cyan hover:underline">
                  <ExternalLink className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                  <span>{d.type}: {d.title}{d.description && <span className="block text-gray-500 text-xs">{d.description}</span>}</span>
                </a>
              ))}
            </div>
            {item.bom_sample && item.bom_sample.length > 0 && (
              <table className="text-xs w-full mb-3">
                <tbody>
                  {item.bom_sample.map((r, i) => (
                    <tr key={i} className="border-b border-cyber-light/10">
                      <td className="py-1 pr-2 font-mono text-cyber-cyan">{r.ref}</td>
                      <td className="py-1 pr-2 text-white">{r.part}</td>
                      <td className="py-1 pr-2 text-gray-400">{r.maker}</td>
                      <td className="py-1 text-gray-500">{r.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="text-xs text-gray-500 mb-3">
              {item.item_type === 'firmware'
                ? 'Check: does the label and file name fit this product (brand, model, category)? Use Flag if the product name was misread from the label.'
                : 'Check: is this the right product/part, revision and category, and do the documents belong to it?'}
            </p>
            <textarea className="input-cyber w-full mb-3 text-sm" rows={2} value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="If flagging: what's wrong? (wrong model, wrong revision, not a schematic, …)" />
            <div className="flex gap-2">
              <button onClick={() => verdict.mutate('correct')} disabled={verdict.isPending}
                className="btn-cyber-green inline-flex items-center gap-1"><Check className="h-4 w-4" /> Correct</button>
              <button onClick={() => verdict.mutate('flagged')} disabled={verdict.isPending || !note.trim()}
                className="btn-cyber-pink inline-flex items-center gap-1 disabled:opacity-40"
                title={note.trim() ? '' : 'Say what is wrong first'}><Flag className="h-4 w-4" /> Flag</button>
            </div>
          </div>
          {item.image && (
            <a href={item.image} target="_blank" rel="noopener noreferrer">
              <img src={item.image} alt="" className="w-full border border-cyber-light/30" />
            </a>
          )}
        </div>
      )}
    </div>
  );
}
