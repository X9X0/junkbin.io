import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Download, ExternalLink, Loader2, MessageSquare, X } from 'lucide-react';
import clsx from 'clsx';
import { products, components } from '../../api/endpoints';
import { parseApiError } from '../../utils/formErrors';
import { useAuth } from '../../context/AuthContext';
import {
  type PendingItem, decide, itemDate, itemFile, itemKey, itemLink, itemTitle, itemUser,
  rejectReasons, typeBadgeColors, typeIcons,
} from './pendingItems';

const CONTINUE_KEY = 'moderation.continueNext';

function readContinue(): boolean {
  try {
    return localStorage.getItem(CONTINUE_KEY) !== 'false';
  } catch {
    return true;
  }
}

function formatSize(bytes?: number | null) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface ReviewViewerProps {
  items: PendingItem[];
  activeKey: string;
  /** Everything pending under the current filter; the list holds the first page of it. */
  total?: number;
  /** Open with the rejection feedback form showing (the table's REJECT button). */
  startRejecting?: boolean;
  onNavigate: (key: string) => void;
  onClose: () => void;
  /** The item was approved or rejected (its key), so the list can drop it at once. */
  onDecided: (key: string) => void;
}

/**
 * Review pending content without leaving the moderation page: the item's file or details
 * in an overlay, approve/reject at the bottom, feedback to the submitter on reject, and
 * (optionally) straight on to the next item.
 */
export default function ReviewViewer({ items, activeKey, total, startRejecting = false, onNavigate, onClose, onDecided }: ReviewViewerProps) {
  const { user } = useAuth();
  const index = items.findIndex((i) => itemKey(i) === activeKey);
  const item = index >= 0 ? items[index] : null;
  const [continueNext, setContinueNext] = useState(readContinue);
  const [rejecting, setRejecting] = useState(startRejecting);
  // feedback and errors belong to one item: a draft for another item reads as empty
  const [draft, setDraft] = useState({ key: activeKey, notes: '', error: null as string | null });
  const notes = draft.key === activeKey ? draft.notes : '';
  const error = draft.key === activeKey ? draft.error : null;
  const setNotes = (update: (current: string) => string) =>
    setDraft({ key: activeKey, notes: update(notes), error: null });
  const setError = (message: string) => setDraft({ key: activeKey, notes, error: message });
  const notesRef = useRef<HTMLTextAreaElement>(null);

  const toggleContinue = (value: boolean) => {
    setContinueNext(value);
    try {
      localStorage.setItem(CONTINUE_KEY, String(value));
    } catch {
      // the choice just isn't remembered
    }
  };

  useEffect(() => {
    if (rejecting) notesRef.current?.focus();
  }, [rejecting, activeKey]);

  // the item left the list (decided elsewhere, or the list ran out)
  useEffect(() => {
    if (!item) onClose();
  }, [item, onClose]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, []);

  const go = (step: number) => {
    const next = items[index + step];
    if (next) {
      setRejecting(false);
      onNavigate(itemKey(next));
    }
  };

  const decision = useMutation({
    mutationFn: ({ target, approve, feedback }: { target: PendingItem; approve: boolean; feedback: string; nextKey: string | null }) =>
      decide(target, approve, feedback),
    onSuccess: (_data, { target, nextKey }) => {
      setRejecting(false);
      onDecided(itemKey(target));
      if (continueNext && nextKey) onNavigate(nextKey);
      else onClose();
    },
    onError: (err) => setError(parseApiError(err, 'Action failed. Please try again.')),
  });

  const submit = (approve: boolean) => {
    if (!item || decision.isPending) return;
    const next = items[index + 1] || items[index - 1];
    decision.mutate({ target: item, approve, feedback: approve ? '' : notes.trim(), nextKey: next ? itemKey(next) : null });
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
      if (e.key === 'Escape') {
        e.preventDefault();
        if (rejecting) setRejecting(false);
        else onClose();
        return;
      }
      if (typing) {
        if (rejecting && e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit(false);
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'ArrowLeft') go(-1);
      else if (e.key === 'ArrowRight') go(1);
      else if (e.key === 'a' && !rejecting) submit(true);
      else if (e.key === 'r' && !rejecting) { e.preventDefault(); setRejecting(true); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  if (!item) return null;

  const TypeIcon = typeIcons[item.type];
  const submitter = itemUser(item);
  // imports are credited to the account that ran them: no feedback to yourself
  const ownItem = !!submitter && submitter === user?.username;
  const reasons = rejectReasons[item.type];
  const addReason = (text: string) => {
    setNotes((current) => (current.includes(text) ? current : current.trim() ? `${current.trim()} ${text}` : text));
    notesRef.current?.focus();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-6" role="dialog" aria-modal="true" aria-label="Review item">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex flex-col w-full max-w-5xl max-h-full bg-cyber-dark border border-cyber-light/30 shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-cyber-light/30">
          <span className={clsx('px-2 py-0.5 text-xs font-mono border inline-flex items-center gap-1 flex-shrink-0', typeBadgeColors[item.type])}>
            <TypeIcon className="h-3 w-3" />
            {item.type.replace('_', ' ').toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-white truncate">{itemTitle(item)}</div>
            <div className="text-xs text-gray-500 font-mono truncate">
              {submitter ? `by ${submitter}` : 'imported'}
              {itemDate(item) && ` · ${new Date(itemDate(item)).toLocaleDateString()}`}
            </div>
          </div>
          <Link to={itemLink(item)} target="_blank" rel="noopener noreferrer" title="Open the item's page in a new tab"
            className="hidden sm:inline-flex items-center gap-1 text-xs font-mono text-gray-500 hover:text-cyber-cyan">
            PAGE <ExternalLink className="h-3 w-3" />
          </Link>
          <div className="flex items-center gap-1 font-mono text-xs text-gray-400">
            <button onClick={() => go(-1)} disabled={index <= 0} className="p-1 hover:text-white disabled:opacity-30" aria-label="Previous item">
              <ChevronLeft className="h-5 w-5" />
            </button>
            <span className="tabular-nums" title={total && total > items.length ? `${items.length} loaded; more load as you decide` : undefined}>
              {index + 1} / {items.length}{total && total > items.length ? ` of ${total}` : ''}
            </span>
            <button onClick={() => go(1)} disabled={index >= items.length - 1} className="p-1 hover:text-white disabled:opacity-30" aria-label="Next item">
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          <ItemContext item={item} />
          <ItemBody item={item} />
        </div>

        {/* Decision */}
        <div className="border-t border-cyber-light/30 px-4 py-3 bg-black/20">
          {error && <div className="text-cyber-pink text-sm font-mono mb-2">{error}</div>}
          {rejecting ? (
            <div>
              {submitter && !ownItem ? (
                <>
                  <div className="flex items-center gap-2 text-sm text-white mb-1">
                    <MessageSquare className="h-4 w-4 text-cyber-pink" />
                    Feedback to <span className="text-cyber-pink">{submitter}</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    Sent by email and as a notification. Say what's wrong and what would make it acceptable.
                  </p>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {reasons.map(([label, text]) => (
                      <button key={label} type="button" onClick={() => addReason(text)}
                        className={clsx('px-2 py-1 text-xs font-mono border transition-colors',
                          notes.includes(text)
                            ? 'border-cyber-pink text-cyber-pink bg-cyber-pink/10'
                            : 'border-cyber-light/30 text-gray-400 hover:text-white hover:border-cyber-pink/60')}>
                        {label}
                      </button>
                    ))}
                  </div>
                  <textarea ref={notesRef} value={notes} onChange={(e) => setNotes(() => e.target.value)} rows={3} maxLength={2000}
                    className="input-cyber w-full text-sm mb-2"
                    placeholder="e.g. The photo shows the charger, not the laptop. A photo of the whole laptop would be accepted." />
                </>
              ) : (
                <p className="text-sm text-gray-400 mb-2">
                  {ownItem ? 'Your own item (imports are credited to you): no feedback is sent.' : 'Imported item: there is no submitter to send feedback to.'}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-2">
                <ContinueToggle checked={continueNext} onChange={toggleContinue} />
                <div className="flex-1" />
                <button onClick={() => setRejecting(false)} className="btn-cyber text-sm" disabled={decision.isPending}>Back</button>
                <button onClick={() => submit(false)} disabled={decision.isPending}
                  className="btn-cyber btn-cyber-pink text-sm inline-flex items-center gap-1 disabled:opacity-50">
                  {decision.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
                  {!submitter || ownItem ? 'Reject' : notes.trim() ? 'Reject and send feedback' : 'Reject without feedback'}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <ContinueToggle checked={continueNext} onChange={toggleContinue} />
              <span className="hidden md:inline text-xs text-gray-600 font-mono">A approve · R reject · ←/→ browse · Esc close</span>
              <div className="flex-1" />
              <button onClick={() => setRejecting(true)} disabled={decision.isPending}
                className="btn-cyber btn-cyber-pink text-sm inline-flex items-center gap-1 disabled:opacity-50">
                <X className="h-4 w-4" /> Reject…
              </button>
              <button onClick={() => submit(true)} disabled={decision.isPending}
                className="btn-cyber btn-cyber-green text-sm inline-flex items-center gap-1 disabled:opacity-50">
                {decision.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Approve
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ContinueToggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="inline-flex items-center gap-2 text-xs font-mono text-gray-400 cursor-pointer select-none">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="accent-cyber-yellow" />
      Continue to next item after decision
    </label>
  );
}

/** What the item belongs to: the product or component, so a photo or file can be judged against it. */
function ItemContext({ item }: { item: PendingItem }) {
  const productId = item.type === 'product' || item.type === 'recipe' || item.type === 'component_image' || item.type === 'datasheet'
    ? null : item.data.product || null;
  const componentId = item.type === 'component_image' || item.type === 'datasheet' ? item.data.component : null;
  const { data: product } = useQuery({
    queryKey: ['moderationContext', 'product', productId],
    queryFn: () => products.get(productId!),
    enabled: !!productId,
    staleTime: 5 * 60 * 1000,
  });
  const { data: component } = useQuery({
    queryKey: ['moderationContext', 'component', componentId],
    queryFn: () => components.get(componentId!),
    enabled: !!componentId,
    staleTime: 5 * 60 * 1000,
  });
  if (product) {
    const photo = product.primary_image?.thumbnail || product.primary_image?.image;
    return (
      <div className="flex items-center gap-3 mb-3 text-sm">
        {photo && item.type !== 'image' && <img src={photo} alt="" className="h-10 w-10 object-contain bg-black/40 border border-cyber-light/20" />}
        <div className="min-w-0">
          <span className="text-gray-500 font-mono text-xs">FOR </span>
          <span className="text-cyber-cyan">{product.manufacturer} {product.model_number}</span>
          {product.revision && <span className="text-gray-400"> · Rev {product.revision}</span>}
          <span className="text-gray-500"> · {product.category_display || product.category}</span>
          {!product.is_approved && <span className="text-cyber-yellow text-xs font-mono"> · PENDING PRODUCT</span>}
        </div>
      </div>
    );
  }
  if (component) {
    return (
      <div className="mb-3 text-sm">
        <span className="text-gray-500 font-mono text-xs">FOR </span>
        <span className="text-cyber-cyan">{component.manufacturer} {component.part_number}</span>
        {component.description && <span className="text-gray-500"> · {component.description}</span>}
      </div>
    );
  }
  return null;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  if (children === undefined || children === null || children === '') return null;
  return (
    <div>
      <dt className="text-xs font-mono text-gray-500">{label}</dt>
      <dd className="text-sm text-gray-200 break-words">{children}</dd>
    </div>
  );
}

function ItemBody({ item }: { item: PendingItem }) {
  const file = itemFile(item);
  switch (item.type) {
    case 'image':
    case 'component_image':
      return (
        <div>
          <ImagePreview src={item.data.image} />
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
            <Field label="CAPTION">{item.data.caption}</Field>
            <Field label="TYPE">{item.data.image_type}</Field>
            {item.type === 'image' && <Field label="SIZE">{item.data.width && item.data.height ? `${item.data.width} × ${item.data.height}` : ''}</Field>}
            <Field label="BACKGROUND">{item.data.background_removed ? 'removed' : ''}</Field>
          </dl>
        </div>
      );
    case 'schematic':
    case 'datasheet':
      return (
        <div>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            {item.type === 'schematic' && <Field label="TYPE">{item.data.schematic_type_display || item.data.schematic_type}</Field>}
            <Field label="VERSION">{item.data.version}</Field>
            <Field label="FILE">{[item.data.file_type?.toUpperCase(), formatSize(item.data.file_size)].filter(Boolean).join(' · ')}</Field>
            <Field label="SOURCE">{item.data.source_url
              ? <a href={item.data.source_url} target="_blank" rel="noopener noreferrer" className="text-cyber-cyan hover:underline">{item.data.source_type}</a>
              : item.data.source_type}</Field>
            {item.type === 'schematic' && <Field label="PAGES">{item.data.page_count}</Field>}
          </dl>
          {item.type === 'schematic' && item.data.description && <p className="text-sm text-gray-300 mb-3">{item.data.description}</p>}
          {item.data.source_notes && <p className="text-xs text-gray-500 mb-3">{item.data.source_notes}</p>}
          {file && <FilePreview key={file.url} url={file.url} type={file.type} />}
        </div>
      );
    case 'firmware':
      return (
        <div>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <Field label="VERSION">{item.data.version}</Field>
            <Field label="CHIP">{item.data.chip_architecture}</Field>
            <Field label="FILE">{[item.data.file_type?.toUpperCase(), formatSize(item.data.file_size)].filter(Boolean).join(' · ')}</Field>
            <Field label="SOURCE">{item.data.source_type_display || item.data.source_type}</Field>
          </dl>
          {item.data.description && <p className="text-sm text-gray-300 mb-3">{item.data.description}</p>}
          {item.data.source_notes && <p className="text-xs text-gray-500 mb-3">{item.data.source_notes}</p>}
          {file && <HexPreview key={file.url} url={file.url} />}
        </div>
      );
    case 'product': {
      const p = item.data;
      const photo = p.primary_image?.medium || p.primary_image?.image;
      return (
        <div className="grid md:grid-cols-[1fr_16rem] gap-4">
          <div>
            <dl className="grid grid-cols-2 gap-3 mb-3">
              <Field label="MAKER">{p.manufacturer}</Field>
              <Field label="MODEL">{p.model_number}</Field>
              <Field label="REVISION">{p.revision}</Field>
              <Field label="REGION">{p.region_display || (p.region !== 'global' ? p.region : '')}</Field>
              <Field label="CATEGORY">{[p.category_display || p.category, p.subcategory].filter(Boolean).join(' · ')}</Field>
              <Field label="YEAR">{p.year_manufactured}</Field>
              <Field label="FCC ID">{p.fcc_id}</Field>
              <Field label="PART NUMBER">{p.part_number}</Field>
              <Field label="CONTENT">{`${p.component_count} parts · ${p.image_count} images · ${p.schematic_count} documents · ${p.firmware_count} firmware`}</Field>
              <Field label="SOURCE">{p.source_url && <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="text-cyber-cyan hover:underline break-all">{p.source_url}</a>}</Field>
            </dl>
            {p.description && <p className="text-sm text-gray-300 whitespace-pre-line">{p.description}</p>}
          </div>
          {photo && <img src={photo} alt="" className="w-full object-contain bg-black/40 border border-cyber-light/20" />}
        </div>
      );
    }
    case 'recipe': {
      const r = item.data;
      return (
        <div className="grid md:grid-cols-[1fr_16rem] gap-4">
          <div>
            <dl className="grid grid-cols-2 gap-3 mb-3">
              <Field label="CATEGORY">{r.category_display || r.category}</Field>
              <Field label="DIFFICULTY">{r.difficulty_display || r.difficulty}</Field>
              <Field label="TIME">{r.estimated_time}</Field>
              <Field label="PARTS">{r.component_count}</Field>
              <Field label="LINK">{r.external_url && <a href={r.external_url} target="_blank" rel="noopener noreferrer" className="text-cyber-cyan hover:underline break-all">{r.external_url}</a>}</Field>
            </dl>
            {r.description && <p className="text-sm text-gray-300 whitespace-pre-line">{r.description}</p>}
          </div>
          {r.image && <img src={r.image} alt="" className="w-full object-contain bg-black/40 border border-cyber-light/20" />}
        </div>
      );
    }
    case 'component_suggestion': {
      const s = item.data;
      return (
        <div>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <Field label="PART NUMBER">{s.part_number}</Field>
            <Field label="MAKER">{s.manufacturer}</Field>
            <Field label="DESIGNATOR">{s.reference_designator}</Field>
            <Field label="TYPE">{s.component_type}</Field>
            <Field label="PACKAGE">{s.package_type}</Field>
            <Field label="VALUE">{s.value_raw}</Field>
            <Field label="QUANTITY">{s.quantity}</Field>
            <Field label="CONFIDENCE">{s.confidence_display || s.confidence}</Field>
            <Field label="SOURCE">{[s.source_type_display || s.source_type, s.page_number ? `page ${s.page_number}` : ''].filter(Boolean).join(', ')}</Field>
            <Field label="MATCHES">{s.matched_component && `${s.matched_component.manufacturer} ${s.matched_component.part_number}`}</Field>
          </dl>
          {s.description && <p className="text-sm text-gray-300 mb-3">{s.description}</p>}
          {s.extraction_context && (
            <pre className="text-xs text-gray-400 bg-black/40 border border-cyber-light/20 p-3 whitespace-pre-wrap">{s.extraction_context}</pre>
          )}
        </div>
      );
    }
  }
}

function ImagePreview({ src }: { src: string }) {
  return (
    <div className="flex items-center justify-center bg-[repeating-conic-gradient(#1f2937_0%_25%,#111827_0%_50%)] bg-[length:20px_20px] border border-cyber-light/20">
      <img src={src} alt="" className="max-h-[60vh] max-w-full object-contain" />
    </div>
  );
}

/** A document inline: PDFs through a blob URL (shown in place whatever the server's headers say), images as images. */
function FilePreview({ url, type }: { url: string; type: string }) {
  const isPdf = type.toLowerCase() === 'pdf' || url.toLowerCase().split('?')[0].endsWith('.pdf');
  const isImage = /^(png|jpe?g|gif|webp|image)$/i.test(type) || /\.(png|jpe?g|gif|webp)(\?|$)/i.test(url);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isPdf) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    fetch(url)
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))))
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
        setBlobUrl(objectUrl);
      })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url, isPdf]);

  if (isImage) return <ImagePreview src={url} />;
  if (isPdf) {
    if (failed) return <iframe src={url} title="Document" className="w-full h-[65vh] bg-white border border-cyber-light/20" />;
    if (!blobUrl) return <div className="h-[65vh] flex items-center justify-center text-gray-500 text-sm"><Loader2 className="h-4 w-4 animate-spin mr-2" />Loading document…</div>;
    return <iframe src={blobUrl} title="Document" className="w-full h-[65vh] bg-white border border-cyber-light/20" />;
  }
  return (
    <a href={url} download className="inline-flex items-center gap-2 text-sm text-cyber-cyan hover:underline">
      <Download className="h-4 w-4" /> No preview for this file type: download it
    </a>
  );
}

const HEX_BYTES = 512;

/** The first bytes of a firmware dump: enough to spot an empty (all FF / 00) read or the wrong file. */
function HexPreview({ url }: { url: string }) {
  const [bytes, setBytes] = useState<Uint8Array | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const r = await fetch(url, { headers: { Range: `bytes=0-${HEX_BYTES - 1}` }, signal: controller.signal });
        const reader = r.body!.getReader();
        const chunks: Uint8Array[] = [];
        let total = 0;
        while (total < HEX_BYTES) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value);
          total += value.length;
        }
        reader.cancel().catch(() => {});
        const out = new Uint8Array(Math.min(total, HEX_BYTES));
        let offset = 0;
        for (const c of chunks) {
          const take = c.subarray(0, out.length - offset);
          out.set(take, offset);
          offset += take.length;
          if (offset >= out.length) break;
        }
        setBytes(out);
      } catch {
        if (!controller.signal.aborted) setFailed(true);
      }
    })();
    return () => controller.abort();
  }, [url]);

  const download = (
    <a href={url} download className="inline-flex items-center gap-1 text-xs font-mono text-cyber-cyan hover:underline">
      <Download className="h-3 w-3" /> DOWNLOAD
    </a>
  );
  if (failed) return <div className="text-sm text-gray-500">Could not read the file. {download}</div>;
  if (!bytes) return <div className="text-sm text-gray-500"><Loader2 className="h-4 w-4 animate-spin inline mr-2" />Reading the first bytes…</div>;

  const blank = bytes.length > 0 && (bytes.every((b) => b === 0xff) || bytes.every((b) => b === 0));
  const rows: string[] = [];
  for (let i = 0; i < bytes.length; i += 16) {
    const row = Array.from(bytes.subarray(i, i + 16));
    const hex = row.map((b) => b.toString(16).padStart(2, '0')).join(' ').padEnd(47, ' ');
    const ascii = row.map((b) => (b >= 0x20 && b < 0x7f ? String.fromCharCode(b) : '.')).join('');
    rows.push(`${i.toString(16).padStart(8, '0')}  ${hex}  ${ascii}`);
  }
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-mono text-gray-500">FIRST {bytes.length} BYTES</span>
        {download}
      </div>
      {blank && <div className="text-xs font-mono text-cyber-yellow mb-1">Every byte shown is {bytes[0] === 0 ? '00' : 'FF'}: possibly an empty or erased read.</div>}
      <pre className="text-[11px] leading-4 text-gray-300 bg-black/40 border border-cyber-light/20 p-3 overflow-x-auto">{rows.join('\n')}</pre>
    </div>
  );
}

/** A single file over the page (image or document), closed with Esc or a click outside. */
export function FileOverlay({ url, type, title, onClose }: { url: string; type: string; title: string; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handler);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-6" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex flex-col w-full max-w-5xl max-h-full bg-cyber-dark border border-cyber-light/30 shadow-2xl">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-cyber-light/30">
          <div className="flex-1 min-w-0 text-white truncate">{title}</div>
          <a href={url} target="_blank" rel="noopener noreferrer" title="Open in a new tab"
            className="inline-flex items-center gap-1 text-xs font-mono text-gray-500 hover:text-cyber-cyan">
            NEW TAB <ExternalLink className="h-3 w-3" />
          </a>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          <FilePreview key={url} url={url} type={type} />
        </div>
      </div>
    </div>
  );
}
