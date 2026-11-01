import { Fragment, useState, useCallback, useEffect, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { products, schematics } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Upload, FileText, Loader2, CheckCircle, AlertTriangle, X, Trash2, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import axios from 'axios';
import type { BomCandidate } from '../types';

interface BomPdfExtractProps {
  productId: string;
  /** If set, scans this existing schematic's own file instead of asking for a fresh upload. */
  schematicId?: string;
  schematicTitle?: string;
  /** 'ocr' scans a circuit diagram for designator labels via OCR instead of parsing text/tables. */
  mode?: 'text' | 'ocr';
  onSuccess?: () => void;
  onClose?: () => void;
}

type Step = 'upload' | 'review' | 'submitted';
type Confidence = BomCandidate['confidence'];
const CONFIDENCES: Confidence[] = ['high', 'medium', 'low'];

export default function BomPdfExtract({ productId, schematicId, schematicTitle, mode = 'text', onSuccess, onClose }: BomPdfExtractProps) {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [step, setStep] = useState<Step>('upload');
  const [candidates, setCandidates] = useState<BomCandidate[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [submitResult, setSubmitResult] = useState<{ created: number } | null>(null);
  // review: rows left out of the submission (low-confidence ones start out), the confidence shown, the row opened
  const [excluded, setExcluded] = useState<Set<number>>(new Set());
  const [shown, setShown] = useState<Confidence | 'all'>('all');
  const [open, setOpen] = useState<number | null>(null);
  const autoTriggered = useRef(false);
  const sourceType = mode === 'ocr' ? 'schematic_ocr' : 'pdf_manual';

  const getErrorMessage = (error: unknown): string => {
    if (axios.isAxiosError(error) && error.response?.status === 429) {
      return t(isAuthenticated ? 'bom_pdf.throttled' : 'bom_pdf.throttled_anon');
    }
    if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
      return error.response.data.detail;
    }
    return t('bom_pdf.error');
  };

  const extractMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return products.extractBomPdf(productId, formData);
    },
    onSuccess: (data) => startReview(data.candidates),
  });

  const extractFromSchematicMutation = useMutation({
    mutationFn: () => (mode === 'ocr' ? schematics.extractBomOcr(schematicId!) : schematics.extractBom(schematicId!)),
    onSuccess: (data) => startReview(data.candidates),
  });

  function startReview(rows: BomCandidate[]) {
    setCandidates(rows);
    setExcluded(new Set(rows.flatMap((c, i) => (c.confidence === 'low' ? [i] : []))));
    setShown('all');
    setOpen(null);
    setStep('review');
  }

  const included = candidates.filter((_, i) => !excluded.has(i));
  const toggle = (i: number) => setExcluded((prev) => {
    const next = new Set(prev);
    if (next.has(i)) next.delete(i);
    else next.add(i);
    return next;
  });
  const setIncluded = (confidence: Confidence, include: boolean) => setExcluded((prev) => {
    const next = new Set(prev);
    candidates.forEach((c, i) => {
      if (c.confidence !== confidence) return;
      if (include) next.delete(i);
      else next.add(i);
    });
    return next;
  });

  useEffect(() => {
    if (schematicId && !autoTriggered.current) {
      autoTriggered.current = true;
      extractFromSchematicMutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schematicId]);

  const submitMutation = useMutation({
    mutationFn: () => products.submitBomSuggestions(productId, included, sourceType),
    onSuccess: (data) => {
      setSubmitResult({ created: data.created });
      setStep('submitted');
      onSuccess?.();
    },
  });

  const handleFileSelect = useCallback((file: File | null) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) return;
    extractMutation.mutate(file);
  }, [extractMutation]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files[0]);
  };

  const updateCandidate = (index: number, updates: Partial<BomCandidate>) => {
    setCandidates((prev) => prev.map((c, i) => (i === index ? { ...c, ...updates } : c)));
  };

  const removeCandidate = (index: number) => {
    setCandidates((prev) => prev.filter((_, i) => i !== index));
    // indexes after the removed row move up by one
    setExcluded((prev) => new Set([...prev].filter((i) => i !== index).map((i) => (i > index ? i - 1 : i))));
    setOpen(null);
  };

  const reset = () => {
    if (schematicId) {
      // Nothing new to pick - re-scanning the same document gives the same
      // result, so "start over" just closes this panel.
      onClose?.();
      return;
    }
    setStep('upload');
    setCandidates([]);
    setSubmitResult(null);
    extractMutation.reset();
    submitMutation.reset();
  };

  const confidenceBadge = (confidence: BomCandidate['confidence']) => clsx(
    'badge-cyber text-[10px]',
    confidence === 'high' && 'text-cyber-green border-cyber-green',
    confidence === 'low' && 'text-cyber-yellow border-cyber-yellow',
    confidence === 'medium' && 'text-gray-400 border-gray-500'
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-semibold text-white">
          <FileText className="h-5 w-5 inline mr-2 text-cyber-cyan" />
          {schematicTitle
            ? t(step === 'upload' ? 'bom_pdf.title_scanning' : 'bom_pdf.title_scanned', { title: schematicTitle })
            : t('bom_pdf.title')}
        </h3>
        {onClose && (
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {step === 'upload' && schematicId && (
        <>
          <p className="text-sm text-gray-500">{mode === 'ocr' ? t('bom_pdf.intro_ocr') : t('bom_pdf.intro')}</p>
          <div className="border-2 border-dashed border-cyber-light/50 p-8 text-center">
            {extractFromSchematicMutation.isError ? (
              <>
                <AlertTriangle className="h-10 w-10 mx-auto mb-3 text-cyber-pink" />
                <p className="text-cyber-pink text-sm font-mono">{getErrorMessage(extractFromSchematicMutation.error)}</p>
              </>
            ) : (
              <>
                <Loader2 className="h-10 w-10 mx-auto mb-3 text-cyber-cyan animate-spin" />
                <p className="text-gray-400">{t('bom_pdf.extracting')}</p>
              </>
            )}
          </div>
        </>
      )}

      {step === 'upload' && !schematicId && (
        <>
          <p className="text-sm text-gray-500">{t('bom_pdf.intro')}</p>
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => document.getElementById('bom-pdf-input')?.click()}
            className={clsx(
              'border-2 border-dashed p-8 text-center cursor-pointer transition-all',
              dragOver
                ? 'border-cyber-cyan bg-cyber-cyan/10'
                : 'border-cyber-light/50 hover:border-cyber-cyan/50 hover:bg-cyber-dark/50'
            )}
          >
            <input
              id="bom-pdf-input"
              type="file"
              accept=".pdf"
              onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
              className="hidden"
            />
            {extractMutation.isPending ? (
              <>
                <Loader2 className="h-10 w-10 mx-auto mb-3 text-cyber-cyan animate-spin" />
                <p className="text-gray-400">{t('bom_pdf.extracting')}</p>
              </>
            ) : (
              <>
                <FileText className={clsx('h-10 w-10 mx-auto mb-3', dragOver ? 'text-cyber-cyan' : 'text-gray-500')} />
                <p className="text-gray-400 mb-1">{t('bom_pdf.drop_hint')}</p>
                <p className="text-xs text-gray-600 font-mono">{t('bom_pdf.drop_accept')}</p>
              </>
            )}
          </div>
          {extractMutation.isError && (
            <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
              <AlertTriangle className="h-4 w-4" />
              {getErrorMessage(extractMutation.error)}
            </div>
          )}
        </>
      )}

      {step === 'review' && (
        <>
          <p className="text-sm text-gray-400">{t('bom_pdf.found_candidates', { count: candidates.length })}</p>

          {candidates.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              {(['all', ...CONFIDENCES] as const).map((c) => (
                <button
                  key={c}
                  onClick={() => setShown(c)}
                  className={clsx('badge-cyber', shown === c ? 'text-cyber-cyan border-cyber-cyan' : 'text-gray-500 border-gray-600')}
                >
                  {c === 'all' ? t('bom_pdf.show_all') : c.toUpperCase()}{' '}
                  ({c === 'all' ? candidates.length : candidates.filter((x) => x.confidence === c).length})
                </button>
              ))}
              <span className="text-gray-600 mx-1">|</span>
              {CONFIDENCES.map((c) => (
                <span key={c} className="flex items-center gap-1">
                  <button onClick={() => setIncluded(c, true)} className="text-cyber-green hover:text-white">
                    {t('bom_pdf.include_all', { level: c.toUpperCase() })}
                  </button>
                  /
                  <button onClick={() => setIncluded(c, false)} className="text-cyber-pink hover:text-white">
                    {t('bom_pdf.exclude_all', { level: c.toUpperCase() })}
                  </button>
                </span>
              ))}
            </div>
          )}

          {candidates.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              {t('bom_pdf.no_candidates')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-cyber-light/30 text-left">
                    <th className="py-2 px-2" />
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_confidence')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_ref')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{mode === 'ocr' ? t('bom_pdf.col_part_or_value') : t('bom_pdf.col_part')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_manufacturer')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_type')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_package')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_qty')}</th>
                    <th className="py-2 px-2 font-mono text-xs text-gray-500">{t('bom_pdf.col_match')}</th>
                    <th className="py-2 px-2" />
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c, i) => (shown !== 'all' && c.confidence !== shown) ? null : (
                    <Fragment key={i}>
                      <tr className={clsx('border-b border-cyber-light/10', excluded.has(i) && 'opacity-40')}>
                        <td className="py-2 px-2 whitespace-nowrap">
                          <input type="checkbox" checked={!excluded.has(i)} onChange={() => toggle(i)}
                                 aria-label={t('bom_pdf.include_row')} className="mr-2 align-middle" />
                          <button onClick={() => setOpen(open === i ? null : i)} className="text-gray-400 hover:text-white align-middle"
                                  aria-label={t('bom_pdf.details')}>
                            {open === i ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </button>
                        </td>
                        <td className="py-2 px-2">
                          <span className={confidenceBadge(c.confidence)}>{c.confidence.toUpperCase()}</span>
                        </td>
                        <td className="py-2 px-2">
                          <input
                            value={c.reference_designator}
                            title={c.reference_designator}
                            onChange={(e) => updateCandidate(i, { reference_designator: e.target.value })}
                            className="input-cyber w-24 py-1 text-xs"
                          />
                        </td>
                        <td className="py-2 px-2">
                          <input
                            value={c.part_number}
                            title={c.part_number}
                            onChange={(e) => updateCandidate(i, { part_number: e.target.value })}
                            className="input-cyber w-48 py-1 text-xs"
                          />
                        </td>
                        <td className="py-2 px-2">
                          <input
                            value={c.manufacturer}
                            onChange={(e) => updateCandidate(i, { manufacturer: e.target.value })}
                            className="input-cyber w-24 py-1 text-xs"
                          />
                        </td>
                        <td className="py-2 px-2 text-gray-400 text-xs whitespace-nowrap">{c.component_type || '-'}</td>
                        <td className="py-2 px-2">
                          <input
                            value={c.package_type}
                            onChange={(e) => updateCandidate(i, { package_type: e.target.value })}
                            className="input-cyber w-16 py-1 text-xs"
                          />
                        </td>
                        <td className="py-2 px-2">
                          <input
                            type="number"
                            min={1}
                            value={c.quantity}
                            onChange={(e) => updateCandidate(i, { quantity: parseInt(e.target.value, 10) || 1 })}
                            className="input-cyber w-14 py-1 text-xs"
                          />
                        </td>
                        <td className="py-2 px-2 text-xs whitespace-nowrap">
                          {c.matched_component ? (
                            <span className="text-cyber-cyan">{t('bom_pdf.matched')}</span>
                          ) : (
                            <span className="text-gray-600">{t('bom_pdf.new')}</span>
                          )}
                        </td>
                        <td className="py-2 px-2">
                          <button
                            onClick={() => removeCandidate(i)}
                            className="text-cyber-pink hover:text-white transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                      {open === i && (
                        <tr className="border-b border-cyber-light/10 bg-cyber-black/40">
                          <td colSpan={10} className="p-3">
                            <RowDetails
                              candidate={c}
                              schematicId={schematicId}
                              onApply={(updates) => updateCandidate(i, updates)}
                            />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <button onClick={reset} className="btn-cyber text-sm py-1.5">
              {schematicId ? t('bom_pdf.cancel') : t('bom_pdf.start_over')}
            </button>
            {!isAuthenticated ? (
              // anyone can scan and look; adding the parts to the product is what an account is for
              <Link to="/register" className="btn-cyber btn-cyber-green flex items-center gap-2">
                <Upload className="h-4 w-4" />
                {t('bom_pdf.signup_to_submit', { count: included.length })}
              </Link>
            ) : (
            <button
              onClick={() => submitMutation.mutate()}
              disabled={included.length === 0 || submitMutation.isPending}
              className={clsx(
                'btn-cyber btn-cyber-green flex items-center gap-2',
                (included.length === 0 || submitMutation.isPending) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {submitMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('bom_pdf.submitting')}
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  {t('bom_pdf.submit_for_review', { count: included.length })}
                </>
              )}
            </button>
            )}
          </div>
          {submitMutation.isError && (
            <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
              <AlertTriangle className="h-4 w-4" />
              {getErrorMessage(submitMutation.error)}
            </div>
          )}
        </>
      )}

      {step === 'submitted' && submitResult && (
        <div className="border border-cyber-green/50 bg-cyber-green/10 p-4 space-y-2">
          <div className="flex items-center gap-2 text-cyber-green text-sm font-mono">
            <CheckCircle className="h-4 w-4 shrink-0" />
            {t('bom_pdf.success', { count: submitResult.created })}
          </div>
          <div className="flex items-start gap-2 text-xs text-gray-400 pl-6">
            <Clock className="h-3 w-3 text-cyber-cyan mt-0.5 shrink-0" />
            <span>{t('bom_pdf.success_review_note')}</span>
          </div>
          <button onClick={reset} className="btn-cyber text-sm py-1.5 mt-2">
            {schematicId ? t('bom_pdf.done') : t('bom_pdf.extract_another')}
          </button>
        </div>
      )}
    </div>
  );
}

/** One row opened: where it was read (a picture of the page around each designator), the words printed
 * there, and other readings to pick from. */
function RowDetails({ candidate: c, schematicId, onApply }: {
  candidate: BomCandidate;
  schematicId?: string;
  onApply: (updates: Partial<BomCandidate>) => void;
}) {
  const { t } = useTranslation();
  const [which, setWhich] = useState(0);
  const locations = c.locations ?? [];
  const loc = locations[Math.min(which, locations.length - 1)];
  return (
    <div className="flex flex-col lg:flex-row gap-4">
      {schematicId && loc && (
        <div className="shrink-0">
          <img
            src={schematics.cropUrl(schematicId, loc)}
            alt={t('bom_pdf.crop_alt', { ref: loc.ref, page: loc.page })}
            className="border border-cyber-light/30 bg-white max-w-full"
            width={520}
            height={320}
            loading="lazy"
          />
          <div className="flex flex-wrap items-center gap-1 mt-1 text-xs font-mono text-gray-500">
            {t('bom_pdf.page_ref', { ref: loc.ref, page: loc.page })}
            {locations.length > 1 && locations.slice(0, 40).map((l, k) => (
              <button key={`${l.ref}-${k}`} onClick={() => setWhich(k)}
                      className={clsx('px-1', k === which ? 'text-cyber-cyan' : 'hover:text-white')}>
                {l.ref}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="space-y-3 text-xs min-w-0">
        {c.description && <p className="text-gray-400 font-mono break-words">{c.description}</p>}
        {(c.label_words ?? []).length > 0 && (
          <div>
            <p className="text-gray-500 mb-1">{t('bom_pdf.label_words')}</p>
            <div className="flex flex-wrap gap-1">
              {(c.label_words ?? []).map((w) => (
                <button key={w} onClick={() => onApply({ part_number: w, value_raw: w })}
                        title={t('bom_pdf.use_as_part')}
                        className="badge-cyber text-gray-300 border-gray-600 hover:text-cyber-cyan hover:border-cyber-cyan">
                  {w}
                </button>
              ))}
            </div>
          </div>
        )}
        {(c.alternatives ?? []).length > 0 && (
          <div>
            <p className="text-gray-500 mb-1">{t('bom_pdf.other_readings')}</p>
            <div className="flex flex-col gap-1 items-start">
              {(c.alternatives ?? []).map((a) => (
                <button key={a.part_number}
                        onClick={() => onApply({ part_number: a.part_number, manufacturer: a.manufacturer,
                                                 component_type: a.component_type, package_type: a.package_type,
                                                 value_raw: a.source })}
                        className="text-left text-cyber-cyan hover:text-white font-mono">
                  {a.part_number}{a.manufacturer && a.manufacturer !== 'Generic' ? ` (${a.manufacturer})` : ''}
                  <span className="text-gray-600"> — {t('bom_pdf.from_word', { word: a.source })}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        <p className="text-gray-600 font-mono">{c.extraction_context}</p>
      </div>
    </div>
  );
}
