import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import {
  Plus,
  Loader2,
  CheckCircle,
  AlertTriangle,
  X,
  ClipboardPaste,
  Layers,
} from 'lucide-react';
import clsx from 'clsx';

interface BatchAddComponentsProps {
  productId: string;
  onSuccess?: () => void;
  onClose?: () => void;
}

interface RowData {
  id: number;
  part_number: string;
  manufacturer: string;
  reference_designator: string;
  quantity: string;
  component_type: string;
  package_type: string;
}

interface BatchResult {
  created: number;
  reused: number;
  linked: number;
  skipped: number;
  errors: { row: number; errors: string[] }[];
  total: number;
}

const COMPONENT_TYPES = [
  { value: '', label: 'Auto-detect' },
  { value: 'ic', label: 'IC' },
  { value: 'mcu', label: 'MCU' },
  { value: 'transistor', label: 'Transistor' },
  { value: 'mosfet', label: 'MOSFET' },
  { value: 'diode', label: 'Diode' },
  { value: 'regulator', label: 'Regulator' },
  { value: 'opamp', label: 'Op-Amp' },
  { value: 'resistor', label: 'Resistor' },
  { value: 'capacitor', label: 'Capacitor' },
  { value: 'inductor', label: 'Inductor' },
  { value: 'crystal', label: 'Crystal' },
  { value: 'connector', label: 'Connector' },
  { value: 'led', label: 'LED' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'fuse', label: 'Fuse' },
  { value: 'other', label: 'Other' },
];

let nextId = 1;

function emptyRow(): RowData {
  return {
    id: nextId++,
    part_number: '',
    manufacturer: '',
    reference_designator: '',
    quantity: '1',
    component_type: '',
    package_type: '',
  };
}

export default function BatchAddComponents({ productId, onSuccess, onClose }: BatchAddComponentsProps) {
  const queryClient = useQueryClient();
  const [rows, setRows] = useState<RowData[]>(() => [emptyRow(), emptyRow(), emptyRow()]);
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [result, setResult] = useState<BatchResult | null>(null);

  const mutation = useMutation({
    mutationFn: (data: { components: any[] }) => products.batchAddComponents(productId, data),
    onSuccess: (data: BatchResult) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'components'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    },
  });

  const updateRow = useCallback((id: number, field: keyof RowData, value: string) => {
    setRows(prev => prev.map(r => r.id === id ? { ...r, [field]: value } : r));
  }, []);

  const addRow = () => setRows(prev => [...prev, emptyRow()]);

  const removeRow = (id: number) => {
    setRows(prev => {
      if (prev.length <= 1) return prev;
      return prev.filter(r => r.id !== id);
    });
  };

  const handlePaste = () => {
    if (!pasteText.trim()) return;

    const lines = pasteText.trim().split('\n');
    const newRows: RowData[] = [];

    for (const line of lines) {
      // Tab-separated (from spreadsheet) or comma-separated
      const cols = line.includes('\t') ? line.split('\t') : line.split(',');
      if (cols.length < 2) continue;

      newRows.push({
        id: nextId++,
        part_number: (cols[0] || '').trim(),
        manufacturer: (cols[1] || '').trim(),
        reference_designator: (cols[2] || '').trim(),
        quantity: (cols[3] || '1').trim(),
        component_type: (cols[4] || '').trim().toLowerCase(),
        package_type: (cols[5] || '').trim(),
      });
    }

    if (newRows.length > 0) {
      setRows(prev => {
        // Replace empty rows, append to non-empty ones
        const nonEmpty = prev.filter(r => r.part_number || r.manufacturer);
        return [...nonEmpty, ...newRows];
      });
      setShowPaste(false);
      setPasteText('');
    }
  };

  const nonEmptyRows = rows.filter(r => r.part_number.trim() || r.manufacturer.trim());
  const validRows = nonEmptyRows.filter(r => r.part_number.trim() && r.manufacturer.trim());
  const invalidRows = nonEmptyRows.filter(r => !r.part_number.trim() || !r.manufacturer.trim());

  const handleSubmit = () => {
    if (validRows.length === 0) return;

    const components = validRows.map(r => ({
      part_number: r.part_number.trim(),
      manufacturer: r.manufacturer.trim(),
      reference_designator: r.reference_designator.trim(),
      quantity: parseInt(r.quantity) || 1,
      component_type: r.component_type || undefined,
      package_type: r.package_type.trim() || undefined,
    }));

    mutation.mutate({ components });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layers className="h-5 w-5 text-cyber-pink" />
          <h3 className="font-display text-lg font-semibold text-white">
            BATCH ADD COMPONENTS
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPaste(!showPaste)}
            className="text-xs text-gray-400 hover:text-cyber-cyan flex items-center gap-1 transition-colors"
          >
            <ClipboardPaste className="h-3.5 w-3.5" />
            Paste
          </button>
          {onClose && (
            <button onClick={onClose} className="text-gray-500 hover:text-white">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Paste area */}
      {showPaste && (
        <div className="p-4 border border-cyber-cyan/30 bg-cyber-cyan/5 space-y-2">
          <p className="text-xs font-mono text-gray-400">
            Paste tab-separated data (Part Number, Manufacturer, Ref Des, Qty, Type, Package):
          </p>
          <textarea
            value={pasteText}
            onChange={e => setPasteText(e.target.value)}
            placeholder={"STM32F405\tSTMicroelectronics\tU1\t1\tmcu\tLQFP-64\nLM1117\tTexas Instruments\tU2\t1\tregulator\tSOT-223"}
            className="w-full h-24 bg-cyber-dark border border-cyber-light/30 text-white text-xs font-mono p-2 focus:border-cyber-cyan focus:outline-none resize-none"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={handlePaste}
              disabled={!pasteText.trim()}
              className="btn-cyber text-xs py-1 disabled:opacity-50"
            >
              Parse & Add Rows
            </button>
            <button
              onClick={() => { setShowPaste(false); setPasteText(''); }}
              className="text-xs text-gray-500 hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Result display */}
      {result && (
        <div className={clsx(
          'p-4 border',
          result.skipped > 0
            ? 'border-cyber-yellow/30 bg-cyber-yellow/5'
            : 'border-cyber-green/30 bg-cyber-green/5'
        )}>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="h-4 w-4 text-cyber-green" />
            <span className="font-mono text-sm text-cyber-green">BATCH ADD COMPLETE</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div>
              <div className="text-xl font-display font-bold text-cyber-green">{result.created}</div>
              <div className="text-[10px] font-mono text-gray-500">CREATED</div>
            </div>
            <div>
              <div className="text-xl font-display font-bold text-cyber-cyan">{result.reused}</div>
              <div className="text-[10px] font-mono text-gray-500">REUSED</div>
            </div>
            <div>
              <div className="text-xl font-display font-bold text-white">{result.linked}</div>
              <div className="text-[10px] font-mono text-gray-500">LINKED</div>
            </div>
            <div>
              <div className="text-xl font-display font-bold text-cyber-yellow">{result.skipped}</div>
              <div className="text-[10px] font-mono text-gray-500">SKIPPED</div>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="mt-3 space-y-1">
              {result.errors.map((err, i) => (
                <div key={i} className="text-xs text-red-400 font-mono">
                  Row {err.row}: {err.errors.join(', ')}
                </div>
              ))}
            </div>
          )}
          <div className="mt-3 flex justify-end">
            <button
              onClick={() => { onSuccess?.(); onClose?.(); }}
              className="btn-cyber text-sm py-1.5"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Table form */}
      {!result && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-cyber-light/30">
                  <th className="py-2 px-1 text-left font-mono text-[10px] text-gray-500 w-[22%]">PART NUMBER *</th>
                  <th className="py-2 px-1 text-left font-mono text-[10px] text-gray-500 w-[22%]">MANUFACTURER *</th>
                  <th className="py-2 px-1 text-left font-mono text-[10px] text-gray-500 w-[12%]">REF DES</th>
                  <th className="py-2 px-1 text-left font-mono text-[10px] text-gray-500 w-[7%]">QTY</th>
                  <th className="py-2 px-1 text-left font-mono text-[10px] text-gray-500 w-[16%]">TYPE</th>
                  <th className="py-2 px-1 text-left font-mono text-[10px] text-gray-500 w-[16%]">PACKAGE</th>
                  <th className="py-2 px-1 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-cyber-light/10">
                    <td className="py-1 px-1">
                      <input
                        type="text"
                        value={row.part_number}
                        onChange={e => updateRow(row.id, 'part_number', e.target.value)}
                        placeholder="e.g. STM32F405"
                        className="w-full bg-transparent border border-cyber-light/20 text-white text-xs px-2 py-1.5 focus:border-cyber-pink focus:outline-none placeholder-gray-700"
                      />
                    </td>
                    <td className="py-1 px-1">
                      <input
                        type="text"
                        value={row.manufacturer}
                        onChange={e => updateRow(row.id, 'manufacturer', e.target.value)}
                        placeholder="e.g. ST Micro"
                        className="w-full bg-transparent border border-cyber-light/20 text-white text-xs px-2 py-1.5 focus:border-cyber-pink focus:outline-none placeholder-gray-700"
                      />
                    </td>
                    <td className="py-1 px-1">
                      <input
                        type="text"
                        value={row.reference_designator}
                        onChange={e => updateRow(row.id, 'reference_designator', e.target.value)}
                        placeholder="U1"
                        className="w-full bg-transparent border border-cyber-light/20 text-white text-xs px-2 py-1.5 focus:border-cyber-cyan focus:outline-none placeholder-gray-700"
                      />
                    </td>
                    <td className="py-1 px-1">
                      <input
                        type="number"
                        min="1"
                        value={row.quantity}
                        onChange={e => updateRow(row.id, 'quantity', e.target.value)}
                        className="w-full bg-transparent border border-cyber-light/20 text-white text-xs px-2 py-1.5 focus:border-cyber-cyan focus:outline-none"
                      />
                    </td>
                    <td className="py-1 px-1">
                      <select
                        value={row.component_type}
                        onChange={e => updateRow(row.id, 'component_type', e.target.value)}
                        className="w-full bg-cyber-dark border border-cyber-light/20 text-white text-xs px-1 py-1.5 focus:border-cyber-cyan focus:outline-none"
                      >
                        {COMPONENT_TYPES.map(ct => (
                          <option key={ct.value} value={ct.value}>{ct.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-1 px-1">
                      <input
                        type="text"
                        value={row.package_type}
                        onChange={e => updateRow(row.id, 'package_type', e.target.value)}
                        placeholder="0402"
                        className="w-full bg-transparent border border-cyber-light/20 text-white text-xs px-2 py-1.5 focus:border-cyber-cyan focus:outline-none placeholder-gray-700"
                      />
                    </td>
                    <td className="py-1 px-1">
                      <button
                        onClick={() => removeRow(row.id)}
                        className="text-gray-600 hover:text-red-400 transition-colors p-0.5"
                        title="Remove row"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Add row button */}
          <button
            onClick={addRow}
            className="text-xs text-gray-500 hover:text-cyber-cyan flex items-center gap-1 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add row
          </button>

          {/* Validation warning */}
          {invalidRows.length > 0 && (
            <div className="p-2 border border-cyber-yellow/30 bg-cyber-yellow/5 text-cyber-yellow text-xs font-mono flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
              {invalidRows.length} row(s) missing required fields and will be skipped.
            </div>
          )}

          {mutation.isError && (
            <div className="p-2 border border-red-500/30 bg-red-500/10 text-red-400 text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              {(mutation.error as any)?.response?.data?.detail || 'Batch add failed.'}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-gray-600 font-mono">
              {validRows.length} valid / {nonEmptyRows.length} filled
            </span>
            <button
              onClick={handleSubmit}
              disabled={validRows.length === 0 || mutation.isPending}
              className="btn-cyber btn-cyber-green text-sm py-1.5 flex items-center gap-2 disabled:opacity-50"
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Add {validRows.length} Component{validRows.length !== 1 ? 's' : ''}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
