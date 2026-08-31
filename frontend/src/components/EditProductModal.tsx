import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { PRODUCT_CATEGORIES, REGIONS } from '../utils/constants';
import { parseApiError } from '../utils/formErrors';
import type { Product } from '../types';

interface EditProductModalProps {
  product: Product;
  isOpen: boolean;
  onClose: () => void;
  isStaff: boolean;
}

export default function EditProductModal({
  product,
  isOpen,
  onClose,
  isStaff,
}: EditProductModalProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');

  const [manufacturer, setManufacturer] = useState('');
  const [modelNumber, setModelNumber] = useState('');
  const [category, setCategory] = useState('');
  const [region, setRegion] = useState('');
  const [revision, setRevision] = useState('');
  const [yearManufactured, setYearManufactured] = useState('');
  const [fccId, setFccId] = useState('');
  const [description, setDescription] = useState('');
  const [teardownNotes, setTeardownNotes] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');

  useEffect(() => {
    if (isOpen) {
      setManufacturer(product.manufacturer || '');
      setModelNumber(product.model_number || '');
      setCategory(product.category || '');
      setRegion(product.region || 'global');
      setRevision(product.revision || '');
      setYearManufactured(product.year_manufactured ? String(product.year_manufactured) : '');
      setFccId(product.fcc_id || '');
      setDescription(product.description || '');
      setTeardownNotes(product.teardown_notes || '');
      setSourceUrl(product.source_url || '');
      setError('');
    }
  }, [isOpen, product]);

  const mutation = useMutation({
    mutationFn: (data: Partial<Product>) => products.update(product.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', product.id] });
      onClose();
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to update product.'));
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Record<string, any> = {
      manufacturer,
      model_number: modelNumber,
      category,
      region,
    };
    if (revision) data.revision = revision;
    if (yearManufactured) data.year_manufactured = parseInt(yearManufactured, 10);
    if (fccId) data.fcc_id = fccId;
    if (description) data.description = description;
    data.teardown_notes = teardownNotes;
    data.source_url = sourceUrl;
    mutation.mutate(data);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">EDIT PRODUCT</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {!isStaff && (
            <div className="flex items-start gap-2 p-3 border border-cyber-yellow/50 bg-cyber-yellow/5 text-sm text-cyber-yellow">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>Editing will reset approval status. Your changes will be reviewed.</span>
            </div>
          )}

          {error && (
            <div className="p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Manufacturer *
              </label>
              <input
                type="text"
                value={manufacturer}
                onChange={(e) => setManufacturer(e.target.value)}
                className="input-cyber"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Model Number *
              </label>
              <input
                type="text"
                value={modelNumber}
                onChange={(e) => setModelNumber(e.target.value)}
                className="input-cyber"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Category *
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input-cyber"
                required
              >
                {PRODUCT_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Region
              </label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="input-cyber"
              >
                {REGIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Revision
              </label>
              <input
                type="text"
                value={revision}
                onChange={(e) => setRevision(e.target.value)}
                className="input-cyber"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Year Manufactured
              </label>
              <input
                type="number"
                value={yearManufactured}
                onChange={(e) => setYearManufactured(e.target.value)}
                min="1970"
                max="2030"
                className="input-cyber"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              FCC ID
            </label>
            <input
              type="text"
              value={fccId}
              onChange={(e) => setFccId(e.target.value)}
              className="input-cyber"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="input-cyber resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Teardown Notes
            </label>
            <textarea
              value={teardownNotes}
              onChange={(e) => setTeardownNotes(e.target.value)}
              rows={5}
              placeholder="Disassembly steps, component locations, repair tips..."
              className="input-cyber resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Source URL
            </label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://..."
              className="input-cyber"
            />
          </div>

          <button
            type="submit"
            disabled={mutation.isPending || !manufacturer || !modelNumber || !category}
            className="w-full btn-cyber py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                SAVING...
              </>
            ) : (
              'SAVE CHANGES'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
