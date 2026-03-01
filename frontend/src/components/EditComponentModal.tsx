import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { components } from '../api/endpoints';
import { X, Loader2 } from 'lucide-react';
import { COMPONENT_TYPES } from '../utils/constants';
import { parseApiError } from '../utils/formErrors';
import DatasheetUpload from './DatasheetUpload';
import type { Component } from '../types';

interface EditComponentModalProps {
  component: Component;
  isOpen: boolean;
  onClose: () => void;
}

export default function EditComponentModal({
  component,
  isOpen,
  onClose,
}: EditComponentModalProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');

  const [manufacturer, setManufacturer] = useState('');
  const [partNumber, setPartNumber] = useState('');
  const [componentType, setComponentType] = useState('');
  const [packageType, setPackageType] = useState('');
  const [typicalFunction, setTypicalFunction] = useState('');
  const [datasheetUrl, setDatasheetUrl] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (isOpen) {
      setManufacturer(component.manufacturer || '');
      setPartNumber(component.part_number || '');
      setComponentType(component.component_type || '');
      setPackageType(component.package_type || '');
      setTypicalFunction(component.typical_function || '');
      setDatasheetUrl(component.datasheet_url || '');
      setDescription(component.description || '');
      setError('');
    }
  }, [isOpen, component]);

  const mutation = useMutation({
    mutationFn: (data: Partial<Component>) => components.update(component.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['component', component.id] });
      onClose();
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to update component.'));
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Record<string, any> = {
      manufacturer,
      part_number: partNumber,
      component_type: componentType,
    };
    if (packageType) data.package_type = packageType;
    if (typicalFunction) data.typical_function = typicalFunction;
    if (datasheetUrl) data.datasheet_url = datasheetUrl;
    if (description) data.description = description;
    mutation.mutate(data);
  };

  const [activeTab, setActiveTab] = useState<'details' | 'datasheets'>('details');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">EDIT COMPONENT</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-cyber-light/30">
          {(['details', 'datasheets'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-xs font-mono uppercase transition-colors ${
                activeTab === tab
                  ? 'text-cyber-cyan border-b-2 border-cyber-cyan'
                  : 'text-gray-500 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === 'datasheets' && (
          <div className="p-4">
            <p className="text-xs text-gray-500 font-mono mb-4">
              Upload a datasheet PDF or image. It will appear on the component page after review.
            </p>
            <DatasheetUpload
              uploadFn={(formData) => components.uploadDatasheet(component.id, formData)}
              invalidateKey={['component', component.id]}
            />
          </div>
        )}

        {activeTab === 'details' && (
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
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
                Part Number *
              </label>
              <input
                type="text"
                value={partNumber}
                onChange={(e) => setPartNumber(e.target.value)}
                className="input-cyber"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Component Type *
              </label>
              <select
                value={componentType}
                onChange={(e) => setComponentType(e.target.value)}
                className="input-cyber"
                required
              >
                {COMPONENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Package Type
              </label>
              <input
                type="text"
                value={packageType}
                onChange={(e) => setPackageType(e.target.value)}
                placeholder="e.g., SOT-23, SOIC-8"
                className="input-cyber"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Typical Function
            </label>
            <input
              type="text"
              value={typicalFunction}
              onChange={(e) => setTypicalFunction(e.target.value)}
              placeholder="e.g., 5V Linear Regulator"
              className="input-cyber"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Datasheet URL
            </label>
            <input
              type="url"
              value={datasheetUrl}
              onChange={(e) => setDatasheetUrl(e.target.value)}
              placeholder="https://..."
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

          <button
            type="submit"
            disabled={mutation.isPending || !manufacturer || !partNumber || !componentType}
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
        )}
      </div>
    </div>
  );
}
