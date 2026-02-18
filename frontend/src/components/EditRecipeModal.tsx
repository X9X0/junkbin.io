import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { recipes } from '../api/endpoints';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { RECIPE_CATEGORIES, DIFFICULTIES } from '../utils/constants';
import { parseApiError } from '../utils/formErrors';
import type { Recipe } from '../types';

interface EditRecipeModalProps {
  recipe: Recipe;
  isOpen: boolean;
  onClose: () => void;
  isStaff: boolean;
}

export default function EditRecipeModal({
  recipe,
  isOpen,
  onClose,
  isStaff,
}: EditRecipeModalProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [category, setCategory] = useState('');
  const [externalUrl, setExternalUrl] = useState('');
  const [estimatedTime, setEstimatedTime] = useState('');
  const [image, setImage] = useState<File | null>(null);

  useEffect(() => {
    if (isOpen) {
      setName(recipe.name || '');
      setDescription(recipe.description || '');
      setDifficulty(recipe.difficulty || 'beginner');
      setCategory(recipe.category || 'other');
      setExternalUrl(recipe.external_url || '');
      setEstimatedTime(recipe.estimated_time || '');
      setImage(null);
      setError('');
    }
  }, [isOpen, recipe]);

  const mutation = useMutation({
    mutationFn: (formData: FormData) => recipes.update(recipe.id, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      onClose();
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to update recipe.'));
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('difficulty', difficulty);
    formData.append('category', category);
    if (externalUrl) formData.append('external_url', externalUrl);
    if (estimatedTime) formData.append('estimated_time', estimatedTime);
    if (image) formData.append('image', image);
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">EDIT RECIPE</h2>
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

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-cyber"
              maxLength={200}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Description *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="input-cyber resize-none"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Difficulty *
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="input-cyber"
                required
              >
                {DIFFICULTIES.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>
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
                {RECIPE_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Tutorial/Instructions URL
            </label>
            <input
              type="url"
              value={externalUrl}
              onChange={(e) => setExternalUrl(e.target.value)}
              placeholder="https://..."
              className="input-cyber"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Estimated Build Time
            </label>
            <input
              type="text"
              value={estimatedTime}
              onChange={(e) => setEstimatedTime(e.target.value)}
              placeholder="e.g. 2-3 hours"
              className="input-cyber"
              maxLength={100}
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Update Image <span className="text-gray-600">(optional)</span>
            </label>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={(e) => setImage(e.target.files?.[0] || null)}
              className="input-cyber text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={mutation.isPending || !name.trim() || !description.trim()}
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
