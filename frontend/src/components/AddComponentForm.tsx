import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { products, components } from '../api/endpoints';
import {
  Search,
  Plus,
  Loader2,
  CheckCircle,
  AlertCircle,
  X,
  Package,
} from 'lucide-react';
import clsx from 'clsx';
import type { Component } from '../types';
import { parseApiError } from '../utils/formErrors';

interface AddComponentFormProps {
  productId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const COMPONENT_TYPES = [
  { value: 'ic', label: 'Integrated Circuit' },
  { value: 'mcu', label: 'Microcontroller' },
  { value: 'transistor', label: 'Transistor' },
  { value: 'mosfet', label: 'MOSFET' },
  { value: 'diode', label: 'Diode' },
  { value: 'regulator', label: 'Voltage Regulator' },
  { value: 'opamp', label: 'Op-Amp' },
  { value: 'resistor', label: 'Resistor' },
  { value: 'capacitor', label: 'Capacitor' },
  { value: 'inductor', label: 'Inductor' },
  { value: 'transformer', label: 'Transformer' },
  { value: 'crystal', label: 'Crystal/Oscillator' },
  { value: 'relay', label: 'Relay' },
  { value: 'connector', label: 'Connector' },
  { value: 'led', label: 'LED' },
  { value: 'display', label: 'Display' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'module', label: 'Module' },
  { value: 'other', label: 'Other' },
];

export default function AddComponentForm({
  productId,
  onSuccess,
  onCancel,
}: AddComponentFormProps) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'search' | 'new'>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedComponent, setSelectedComponent] = useState<Component | null>(null);

  // Form fields for linking
  const [referenceDesignator, setReferenceDesignator] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [locationDescription, setLocationDescription] = useState('');
  const [notes, setNotes] = useState('');

  // New component fields
  const [newComponent, setNewComponent] = useState({
    part_number: '',
    manufacturer: '',
    component_type: '',
    package_type: '',
    description: '',
    datasheet_url: '',
  });

  // Search for components
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['componentSearch', searchQuery],
    queryFn: () => components.search(searchQuery),
    enabled: searchQuery.length >= 2 && mode === 'search',
  });

  // Add component mutation
  const addMutation = useMutation({
    mutationFn: async (data: any) => {
      return products.addComponent(productId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'components'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
      onSuccess?.();
    },
  });

  const handleSubmit = () => {
    const data: any = {
      reference_designator: referenceDesignator,
      quantity: parseInt(quantity, 10) || 1,
      location_description: locationDescription,
      notes,
    };

    if (mode === 'search' && selectedComponent) {
      data.component_id = selectedComponent.id;
    } else if (mode === 'new') {
      data.new_component = newComponent;
    }

    addMutation.mutate(data);
  };

  const isValid =
    (mode === 'search' && selectedComponent) ||
    (mode === 'new' &&
      newComponent.part_number &&
      newComponent.manufacturer &&
      newComponent.component_type);

  return (
    <div className="space-y-6">
      {/* Mode selector */}
      <div className="flex flex-col sm:flex-row gap-2">
        <button
          onClick={() => {
            setMode('search');
            setSelectedComponent(null);
          }}
          className={clsx(
            'flex-1 py-2 px-3 sm:px-4 border font-mono text-xs sm:text-sm transition-colors flex items-center justify-center gap-2',
            mode === 'search'
              ? 'border-cyber-pink bg-cyber-pink/10 text-cyber-pink'
              : 'border-cyber-light/50 text-gray-400 hover:border-cyber-light'
          )}
        >
          <Search className="h-4 w-4" />
          <span>SEARCH EXISTING</span>
        </button>
        <button
          onClick={() => {
            setMode('new');
            setSelectedComponent(null);
          }}
          className={clsx(
            'flex-1 py-2 px-3 sm:px-4 border font-mono text-xs sm:text-sm transition-colors flex items-center justify-center gap-2',
            mode === 'new'
              ? 'border-cyber-pink bg-cyber-pink/10 text-cyber-pink'
              : 'border-cyber-light/50 text-gray-400 hover:border-cyber-light'
          )}
        >
          <Plus className="h-4 w-4" />
          <span>ADD NEW</span>
        </button>
      </div>

      {/* Search mode */}
      {mode === 'search' && (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              SEARCH COMPONENTS
            </label>
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by part number or manufacturer..."
                className="input-cyber pl-10"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            </div>
          </div>

          {/* Search results */}
          {isSearching && (
            <div className="text-center py-4 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin mx-auto" />
            </div>
          )}

          {searchResults && searchResults.length > 0 && (
            <div className="max-h-48 overflow-y-auto border border-cyber-light/30 divide-y divide-cyber-light/20">
              {searchResults.map((comp: Component) => (
                <button
                  key={comp.id}
                  onClick={() => setSelectedComponent(comp)}
                  className={clsx(
                    'w-full p-3 text-left hover:bg-cyber-light/10 transition-colors',
                    selectedComponent?.id === comp.id && 'bg-cyber-pink/10 border-l-2 border-cyber-pink'
                  )}
                >
                  <div className="font-mono text-white">{comp.part_number}</div>
                  <div className="text-xs text-gray-500">
                    {comp.manufacturer} • {comp.component_type_display || comp.component_type}
                  </div>
                </button>
              ))}
            </div>
          )}

          {searchQuery.length >= 2 && searchResults?.length === 0 && (
            <div className="text-center py-4 text-gray-500 text-sm">
              No components found. Try{' '}
              <button
                onClick={() => setMode('new')}
                className="text-cyber-pink hover:underline"
              >
                adding a new one
              </button>
              .
            </div>
          )}

          {/* Selected component preview */}
          {selectedComponent && (
            <div className="p-3 border border-cyber-pink/50 bg-cyber-pink/10">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-mono text-cyber-pink">{selectedComponent.part_number}</div>
                  <div className="text-xs text-gray-400">
                    {selectedComponent.manufacturer} • {selectedComponent.component_type_display}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedComponent(null)}
                  className="p-1 text-gray-500 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* New component mode */}
      {mode === 'new' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                PART NUMBER <span className="text-cyber-pink">*</span>
              </label>
              <input
                type="text"
                value={newComponent.part_number}
                onChange={(e) =>
                  setNewComponent((prev) => ({ ...prev, part_number: e.target.value }))
                }
                placeholder="e.g., LM7805"
                className="input-cyber"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                MANUFACTURER <span className="text-cyber-pink">*</span>
              </label>
              <input
                type="text"
                value={newComponent.manufacturer}
                onChange={(e) =>
                  setNewComponent((prev) => ({ ...prev, manufacturer: e.target.value }))
                }
                placeholder="e.g., Texas Instruments"
                className="input-cyber"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                TYPE <span className="text-cyber-pink">*</span>
              </label>
              <select
                value={newComponent.component_type}
                onChange={(e) =>
                  setNewComponent((prev) => ({ ...prev, component_type: e.target.value }))
                }
                className="input-cyber"
              >
                <option value="">Select type...</option>
                {COMPONENT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-500 mb-1">
                PACKAGE
              </label>
              <input
                type="text"
                value={newComponent.package_type}
                onChange={(e) =>
                  setNewComponent((prev) => ({ ...prev, package_type: e.target.value }))
                }
                placeholder="e.g., SOT-23, SOIC-8"
                className="input-cyber"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              DATASHEET URL
            </label>
            <input
              type="url"
              value={newComponent.datasheet_url}
              onChange={(e) =>
                setNewComponent((prev) => ({ ...prev, datasheet_url: e.target.value }))
              }
              placeholder="https://..."
              className="input-cyber"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              DESCRIPTION
            </label>
            <input
              type="text"
              value={newComponent.description}
              onChange={(e) =>
                setNewComponent((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder="Brief description..."
              className="input-cyber"
            />
          </div>
        </div>
      )}

      {/* Location details (both modes) */}
      <div className="border-t border-cyber-light/30 pt-4 space-y-4">
        <h4 className="font-mono text-sm text-gray-400">LOCATION ON PRODUCT</h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              REFERENCE DESIGNATOR
            </label>
            <input
              type="text"
              value={referenceDesignator}
              onChange={(e) => setReferenceDesignator(e.target.value)}
              placeholder="e.g., U1, R5, C12"
              className="input-cyber"
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-1">
              QUANTITY
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              min="1"
              className="input-cyber"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-mono text-gray-500 mb-1">
            LOCATION DESCRIPTION
          </label>
          <input
            type="text"
            value={locationDescription}
            onChange={(e) => setLocationDescription(e.target.value)}
            placeholder="e.g., Near HDMI port, on power board"
            className="input-cyber"
          />
        </div>

        <div>
          <label className="block text-xs font-mono text-gray-500 mb-1">
            NOTES
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional notes..."
            rows={2}
            className="input-cyber resize-none"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-cyber-light/30">
        {onCancel && (
          <button onClick={onCancel} className="text-gray-400 hover:text-white text-sm font-mono">
            CANCEL
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={!isValid || addMutation.isPending}
          className={clsx(
            'btn-cyber flex items-center gap-2',
            (!isValid || addMutation.isPending) && 'opacity-50 cursor-not-allowed'
          )}
        >
          {addMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              ADDING...
            </>
          ) : (
            <>
              <Package className="h-4 w-4" />
              ADD COMPONENT
            </>
          )}
        </button>
      </div>

      {/* Success message */}
      {addMutation.isSuccess && (
        <div className="flex items-center gap-2 p-3 border border-cyber-green/50 bg-cyber-green/10 text-cyber-green text-sm font-mono">
          <CheckCircle className="h-4 w-4" />
          Component added successfully!
        </div>
      )}

      {/* Error message */}
      {addMutation.isError && (
        <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
          <AlertCircle className="h-4 w-4" />
          {parseApiError(addMutation.error, 'Failed to add component. Please try again.')}
        </div>
      )}
    </div>
  );
}
