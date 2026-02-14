import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { junkbin } from '../api/endpoints';
import { X, Trash2, Loader2, Check } from 'lucide-react';
import clsx from 'clsx';
import type { JunkbinItem } from '../types';

interface AddToJunkbinModalProps {
  contentType: 'product' | 'component';
  objectId: string;
  itemName: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function AddToJunkbinModal({
  contentType,
  objectId,
  itemName,
  isOpen,
  onClose,
}: AddToJunkbinModalProps) {
  const queryClient = useQueryClient();
  const [itemType, setItemType] = useState<'have' | 'want'>('have');
  const [status, setStatus] = useState('not_for_trade');
  const [condition, setCondition] = useState('unknown');
  const [visibility, setVisibility] = useState('public');
  const [notes, setNotes] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const { data: checkData, isLoading: checking } = useQuery({
    queryKey: ['junkbin-check', contentType, objectId],
    queryFn: () => junkbin.check(contentType, objectId),
    enabled: isOpen,
  });

  const existingItems = checkData?.items || [];

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof junkbin.create>[0]) => junkbin.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['junkbin-check', contentType, objectId] });
      queryClient.invalidateQueries({ queryKey: ['junkbin'] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<JunkbinItem> }) =>
      junkbin.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['junkbin-check', contentType, objectId] });
      queryClient.invalidateQueries({ queryKey: ['junkbin'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => junkbin.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['junkbin-check', contentType, objectId] });
      queryClient.invalidateQueries({ queryKey: ['junkbin'] });
      setConfirmDelete(null);
    },
  });

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setItemType('have');
      setStatus('not_for_trade');
      setCondition('unknown');
      setVisibility('public');
      setNotes('');
      setQuantity(1);
      setConfirmDelete(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const hasHave = existingItems.some((i) => i.item_type === 'have');
  const hasWant = existingItems.some((i) => i.item_type === 'want');
  const canAdd = (itemType === 'have' && !hasHave) || (itemType === 'want' && !hasWant);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      content_type: contentType,
      object_id: objectId,
      item_type: itemType,
      status: itemType === 'have' ? status : 'not_for_trade',
      condition: itemType === 'have' ? condition : 'unknown',
      visibility,
      notes,
      quantity,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">
            ADD TO JUNKBIN
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4">
          {/* Item being added */}
          <div className="mb-4 p-3 bg-cyber-dark border border-cyber-light/20">
            <div className="text-xs text-gray-500 uppercase font-mono">{contentType}</div>
            <div className="text-white font-semibold">{itemName}</div>
          </div>

          {checking ? (
            <div className="py-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-cyber-cyan" />
            </div>
          ) : (
            <>
              {/* Existing items */}
              {existingItems.length > 0 && (
                <div className="mb-4 space-y-2">
                  <h3 className="text-xs font-mono text-gray-500 uppercase">Already in your junkbin</h3>
                  {existingItems.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 border border-cyber-light/20 bg-cyber-dark flex items-center justify-between"
                    >
                      <div>
                        <span className={clsx(
                          'badge-cyber text-[10px] mr-2',
                          item.item_type === 'have'
                            ? 'text-cyber-green border-cyber-green'
                            : 'text-cyber-yellow border-cyber-yellow'
                        )}>
                          {item.item_type.toUpperCase()}
                        </span>
                        <span className="text-sm text-gray-300">
                          {item.item_type === 'have' && (
                            <>
                              {item.status === 'available' ? 'For Trade' : 'Not for Trade'}
                              {' · '}
                              {item.condition}
                            </>
                          )}
                          {item.quantity > 1 && ` · ×${item.quantity}`}
                        </span>
                      </div>
                      {confirmDelete === item.id ? (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => deleteMutation.mutate(item.id)}
                            disabled={deleteMutation.isPending}
                            className="text-xs text-cyber-pink hover:text-white"
                          >
                            {deleteMutation.isPending ? 'Removing...' : 'Confirm'}
                          </button>
                          <button
                            onClick={() => setConfirmDelete(null)}
                            className="text-xs text-gray-500 hover:text-white"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDelete(item.id)}
                          className="text-gray-500 hover:text-cyber-pink"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Add new form */}
              {(hasHave && hasWant) ? (
                <div className="py-4 text-center text-gray-400 text-sm">
                  This item is already in both your "have" and "want" lists.
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Item type */}
                  <div>
                    <label className="text-xs font-mono text-gray-500 uppercase block mb-2">
                      Type
                    </label>
                    <div className="flex gap-2">
                      {(!hasHave || itemType === 'have') && (
                        <button
                          type="button"
                          onClick={() => setItemType('have')}
                          disabled={hasHave}
                          className={clsx(
                            'flex-1 py-2 text-sm font-mono border transition-colors',
                            itemType === 'have'
                              ? 'border-cyber-green text-cyber-green bg-cyber-green/10'
                              : 'border-cyber-light/30 text-gray-500 hover:border-gray-400',
                            hasHave && 'opacity-40 cursor-not-allowed'
                          )}
                        >
                          I HAVE THIS
                        </button>
                      )}
                      {(!hasWant || itemType === 'want') && (
                        <button
                          type="button"
                          onClick={() => setItemType('want')}
                          disabled={hasWant}
                          className={clsx(
                            'flex-1 py-2 text-sm font-mono border transition-colors',
                            itemType === 'want'
                              ? 'border-cyber-yellow text-cyber-yellow bg-cyber-yellow/10'
                              : 'border-cyber-light/30 text-gray-500 hover:border-gray-400',
                            hasWant && 'opacity-40 cursor-not-allowed'
                          )}
                        >
                          I WANT THIS
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Have-specific fields */}
                  {itemType === 'have' && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                            Status
                          </label>
                          <select
                            value={status}
                            onChange={(e) => setStatus(e.target.value)}
                            className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                          >
                            <option value="not_for_trade">Not for Trade</option>
                            <option value="available">Available for Trade</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                            Condition
                          </label>
                          <select
                            value={condition}
                            onChange={(e) => setCondition(e.target.value)}
                            className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                          >
                            <option value="new">New</option>
                            <option value="working">Working</option>
                            <option value="broken">Broken / For Parts</option>
                            <option value="unknown">Unknown</option>
                          </select>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Common fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                        Visibility
                      </label>
                      <select
                        value={visibility}
                        onChange={(e) => setVisibility(e.target.value)}
                        className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                      >
                        <option value="public">Public</option>
                        <option value="private">Private</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                        Quantity
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={quantity}
                        onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                        className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white focus:border-cyber-cyan focus:outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-mono text-gray-500 uppercase block mb-1">
                      Notes <span className="text-gray-600">(optional)</span>
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      maxLength={500}
                      rows={2}
                      placeholder="Any notes about this item..."
                      className="w-full bg-cyber-dark border border-cyber-light/50 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-cyber-cyan focus:outline-none resize-none"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={!canAdd || createMutation.isPending}
                    className={clsx(
                      'w-full py-2.5 font-mono text-sm flex items-center justify-center gap-2 transition-colors',
                      canAdd
                        ? 'btn-cyber'
                        : 'border border-gray-600 text-gray-600 cursor-not-allowed'
                    )}
                  >
                    {createMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        ADDING...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4" />
                        ADD TO JUNKBIN
                      </>
                    )}
                  </button>

                  {createMutation.isError && (
                    <p className="text-cyber-pink text-xs text-center">
                      Failed to add item. Please try again.
                    </p>
                  )}
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
