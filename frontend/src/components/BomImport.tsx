import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import {
  Upload,
  FileSpreadsheet,
  Loader2,
  CheckCircle,
  AlertTriangle,
  X,
  ChevronRight,
  ChevronLeft,
  Eye,
} from 'lucide-react';
import clsx from 'clsx';

interface BomImportProps {
  productId: string;
  onSuccess?: () => void;
  onClose?: () => void;
}

type Step = 'upload' | 'mapping' | 'review';

interface ParseResult {
  headers: string[];
  preview_rows: Record<string, string>[];
  detected_mapping: Record<string, string>;
  available_fields: [string, string][];
  total_rows: number;
}

interface ImportResult {
  created: number;
  reused: number;
  linked: number;
  skipped: number;
  errors: { row: number; errors: string[]; data: Record<string, string> }[];
  total: number;
  dry_run: boolean;
}

export default function BomImport({ productId, onSuccess, onClose }: BomImportProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Parse mutation
  const parseMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return products.parseBom(productId, formData);
    },
    onSuccess: (data: ParseResult) => {
      setParseResult(data);
      setColumnMapping(data.detected_mapping);
      setStep('mapping');
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: ({ dryRun }: { dryRun: boolean }) => {
      const formData = new FormData();
      formData.append('file', file!);
      formData.append('column_mapping', JSON.stringify(columnMapping));
      if (dryRun) formData.append('dry_run', 'true');
      return products.importBom(productId, formData);
    },
    onSuccess: (data: ImportResult) => {
      setImportResult(data);
      if (!data.dry_run) {
        queryClient.invalidateQueries({ queryKey: ['product', productId, 'components'] });
        queryClient.invalidateQueries({ queryKey: ['product', productId] });
      }
    },
  });

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && (dropped.name.endsWith('.csv') || dropped.type === 'text/csv')) {
      setFile(dropped);
      parseMutation.mutate(dropped);
    }
  }, [parseMutation]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      parseMutation.mutate(selected);
    }
  }, [parseMutation]);

  const handleMappingChange = (header: string, field: string) => {
    setColumnMapping(prev => {
      const next = { ...prev };
      if (field === '') {
        delete next[header];
      } else {
        next[header] = field;
      }
      return next;
    });
  };

  const mappedFields = new Set(Object.values(columnMapping));
  const hasRequiredFields = mappedFields.has('part_number') && mappedFields.has('manufacturer');

  const reset = () => {
    setStep('upload');
    setFile(null);
    setParseResult(null);
    setColumnMapping({});
    setImportResult(null);
    parseMutation.reset();
    importMutation.reset();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileSpreadsheet className="h-5 w-5 text-cyber-green" />
          <h3 className="font-display text-lg font-semibold text-white">
            IMPORT BOM
          </h3>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 text-xs font-mono">
        {(['upload', 'mapping', 'review'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            {i > 0 && <ChevronRight className="h-3 w-3 text-gray-600" />}
            <span className={clsx(
              'px-2 py-1',
              step === s
                ? 'text-cyber-green bg-cyber-green/10 border border-cyber-green/30'
                : s === 'upload' && step !== 'upload'
                  ? 'text-gray-400'
                  : 'text-gray-600'
            )}>
              {i + 1}. {s.toUpperCase()}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <div>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleFileDrop}
            className={clsx(
              'border-2 border-dashed p-8 text-center transition-all cursor-pointer',
              dragOver
                ? 'border-cyber-green bg-cyber-green/10'
                : 'border-cyber-light/30 hover:border-cyber-green/50'
            )}
            onClick={() => document.getElementById('bom-file-input')?.click()}
          >
            <input
              id="bom-file-input"
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            {parseMutation.isPending ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-10 w-10 text-cyber-green animate-spin" />
                <p className="text-gray-400 font-mono text-sm">PARSING CSV...</p>
              </div>
            ) : (
                <div className="flex flex-col items-center gap-3">
                <Upload className="h-10 w-10 text-gray-500" />
                <p className="text-gray-400">
                  Drag & drop a CSV file here, or click to browse
                </p>
                <p className="text-gray-600 text-xs font-mono">
                  .CSV files only · max 5MB
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider">Compatible with</span>
                  <a
                    href="https://pcbtracer.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-[10px] font-mono px-2 py-0.5 border border-cyber-cyan/30 text-cyber-cyan hover:border-cyber-cyan/60 transition-colors"
                  >
                    PCBTracer
                  </a>
                  <span className="text-[10px] font-mono px-2 py-0.5 border border-cyber-light/20 text-gray-500">
                    KiCad BOM
                  </span>
                </div>
              </div>
            )}
          </div>

          {parseMutation.isError && (
            <div className="mt-4 p-3 border border-red-500/30 bg-red-500/10 text-red-400 text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              {(parseMutation.error as any)?.response?.data?.detail || 'Failed to parse CSV file.'}
            </div>
          )}
        </div>
      )}

      {/* Step 2: Column Mapping */}
      {step === 'mapping' && parseResult && (
        <div className="space-y-4">
          <div className="text-sm text-gray-400 font-mono">
            {parseResult.total_rows} rows detected
            {file && <span className="ml-2 text-gray-600">({file.name})</span>}
          </div>

          {/* Mapping table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-cyber-light/30">
                  <th className="py-2 px-3 text-left font-mono text-xs text-gray-500">CSV COLUMN</th>
                  <th className="py-2 px-3 text-left font-mono text-xs text-gray-500">MAP TO</th>
                  <th className="py-2 px-3 text-left font-mono text-xs text-gray-500">SAMPLE DATA</th>
                </tr>
              </thead>
              <tbody>
                {parseResult.headers.map((header) => (
                  <tr key={header} className="border-b border-cyber-light/20">
                    <td className="py-2 px-3 font-mono text-white text-xs">{header}</td>
                    <td className="py-2 px-3">
                      <select
                        value={columnMapping[header] || ''}
                        onChange={(e) => handleMappingChange(header, e.target.value)}
                        className="bg-cyber-dark border border-cyber-light/30 text-white text-xs px-2 py-1 w-full focus:border-cyber-green focus:outline-none"
                      >
                        <option value="">-- Skip --</option>
                        {parseResult.available_fields.map(([value, label]) => (
                          <option
                            key={value}
                            value={value}
                            disabled={mappedFields.has(value) && columnMapping[header] !== value}
                          >
                            {label} {(value === 'part_number' || value === 'manufacturer') ? '*' : ''}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 px-3 text-gray-500 text-xs truncate max-w-[200px]">
                      {parseResult.preview_rows[0]?.[header] || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!hasRequiredFields && (
            <div className="p-3 border border-cyber-yellow/30 bg-cyber-yellow/10 text-cyber-yellow text-xs font-mono flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              Part Number and Manufacturer columns must be mapped to proceed.
            </div>
          )}

          {/* Preview table with mapped data */}
          {hasRequiredFields && parseResult.preview_rows.length > 0 && (
            <div>
              <h4 className="font-mono text-xs text-gray-500 mb-2">PREVIEW (first {parseResult.preview_rows.length} rows)</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-cyber-light/30">
                      {Object.entries(columnMapping).map(([header, field]) => (
                        <th key={header} className="py-1 px-2 text-left font-mono text-cyber-green">
                          {parseResult.available_fields.find(([v]) => v === field)?.[1] || field}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {parseResult.preview_rows.map((row, i) => (
                      <tr key={i} className="border-b border-cyber-light/10">
                        {Object.keys(columnMapping).map((header) => (
                          <td key={header} className="py-1 px-2 text-gray-400 truncate max-w-[150px]">
                            {row[header] || '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <button onClick={reset} className="text-gray-500 hover:text-white text-sm flex items-center gap-1">
              <ChevronLeft className="h-4 w-4" />
              Back
            </button>
            <button
              onClick={() => setStep('review')}
              disabled={!hasRequiredFields}
              className={clsx(
                'btn-cyber text-sm py-1.5 flex items-center gap-2',
                !hasRequiredFields && 'opacity-50 cursor-not-allowed'
              )}
            >
              Continue
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Import */}
      {step === 'review' && parseResult && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="card-cyber p-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">File</span>
              <span className="text-white font-mono">{file?.name}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Total rows</span>
              <span className="text-white font-mono">{parseResult.total_rows}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Mapped columns</span>
              <span className="text-white font-mono">{Object.keys(columnMapping).length}</span>
            </div>
          </div>

          {/* Import result */}
          {importResult && (
            <div className={clsx(
              'p-4 border',
              importResult.dry_run
                ? 'border-cyber-cyan/30 bg-cyber-cyan/5'
                : importResult.skipped > 0
                  ? 'border-cyber-yellow/30 bg-cyber-yellow/5'
                  : 'border-cyber-green/30 bg-cyber-green/5'
            )}>
              <div className="flex items-center gap-2 mb-3">
                {importResult.dry_run ? (
                  <>
                    <Eye className="h-4 w-4 text-cyber-cyan" />
                    <span className="font-mono text-sm text-cyber-cyan">DRY RUN PREVIEW</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 text-cyber-green" />
                    <span className="font-mono text-sm text-cyber-green">IMPORT COMPLETE</span>
                  </>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div>
                  <div className="text-xl font-display font-bold text-cyber-green">{importResult.created}</div>
                  <div className="text-[10px] font-mono text-gray-500">CREATED</div>
                </div>
                <div>
                  <div className="text-xl font-display font-bold text-cyber-cyan">{importResult.reused}</div>
                  <div className="text-[10px] font-mono text-gray-500">REUSED</div>
                </div>
                <div>
                  <div className="text-xl font-display font-bold text-white">{importResult.linked}</div>
                  <div className="text-[10px] font-mono text-gray-500">LINKED</div>
                </div>
                <div>
                  <div className="text-xl font-display font-bold text-cyber-yellow">{importResult.skipped}</div>
                  <div className="text-[10px] font-mono text-gray-500">SKIPPED</div>
                </div>
              </div>

              {/* Row errors */}
              {importResult.errors.length > 0 && (
                <div className="mt-3 space-y-1 max-h-40 overflow-y-auto">
                  <div className="text-xs font-mono text-gray-500 mb-1">ERRORS:</div>
                  {importResult.errors.map((err, i) => (
                    <div key={i} className="text-xs text-red-400 font-mono">
                      Row {err.row}: {err.errors.join(', ')}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {importMutation.isError && (
            <div className="p-3 border border-red-500/30 bg-red-500/10 text-red-400 text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              {(importMutation.error as any)?.response?.data?.detail || 'Import failed.'}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => {
                setImportResult(null);
                importMutation.reset();
                setStep('mapping');
              }}
              disabled={importMutation.isPending}
              className="text-gray-500 hover:text-white text-sm flex items-center gap-1"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </button>
            <div className="flex items-center gap-3">
              {/* Show dry run if not yet imported */}
              {(!importResult || importResult.dry_run) && (
                <>
                  <button
                    onClick={() => importMutation.mutate({ dryRun: true })}
                    disabled={importMutation.isPending}
                    className="text-sm text-cyber-cyan hover:text-white flex items-center gap-1 disabled:opacity-50"
                  >
                    {importMutation.isPending && importResult?.dry_run !== false ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                    Preview
                  </button>
                  <button
                    onClick={() => importMutation.mutate({ dryRun: false })}
                    disabled={importMutation.isPending}
                    className="btn-cyber btn-cyber-green text-sm py-1.5 flex items-center gap-2 disabled:opacity-50"
                  >
                    {importMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    Import
                  </button>
                </>
              )}

              {/* After successful import */}
              {importResult && !importResult.dry_run && (
                <button
                  onClick={() => {
                    onSuccess?.();
                    onClose?.();
                  }}
                  className="btn-cyber text-sm py-1.5"
                >
                  Done
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
