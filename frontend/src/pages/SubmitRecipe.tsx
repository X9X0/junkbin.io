import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { recipes, components } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2, Search, ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import type { Component } from '../types';
import { parseApiError } from '../utils/formErrors';
import { RECIPE_CATEGORIES, DIFFICULTIES } from '../utils/constants';
import ModerationNotice from '../components/ModerationNotice';

interface BomEntry {
  component: Component;
  quantity: number;
  notes: string;
  is_optional: boolean;
}

export default function SubmitRecipe() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [submittedRecipe, setSubmittedRecipe] = useState<{ id: string; name: string } | null>(null);

  // Step 1 fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [difficulty, setDifficulty] = useState('beginner');
  const [category, setCategory] = useState('other');
  const [externalUrl, setExternalUrl] = useState('');
  const [estimatedTime, setEstimatedTime] = useState('');
  const [image, setImage] = useState<File | null>(null);

  // Step 2 fields
  const [bomEntries, setBomEntries] = useState<BomEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Component[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const submitMutation = useMutation({
    mutationFn: (formData: FormData) => recipes.create(formData),
    onSuccess: (data) => {
      setSubmittedRecipe({ id: data.id, name: data.name });
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to submit recipe. Please try again.'));
    },
  });

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const results = await components.search(searchQuery);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const addComponent = (component: Component) => {
    if (bomEntries.some((e) => e.component.id === component.id)) return;
    setBomEntries([
      ...bomEntries,
      { component, quantity: 1, notes: '', is_optional: false },
    ]);
    setSearchResults([]);
    setSearchQuery('');
  };

  const removeComponent = (index: number) => {
    setBomEntries(bomEntries.filter((_, i) => i !== index));
  };

  const updateEntry = (index: number, updates: Partial<BomEntry>) => {
    setBomEntries(
      bomEntries.map((entry, i) => (i === index ? { ...entry, ...updates } : entry))
    );
  };

  const handleSubmit = () => {
    if (bomEntries.length === 0) {
      setError(t('submit_recipe.bom_empty'));
      return;
    }

    setError('');
    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('difficulty', difficulty);
    formData.append('category', category);
    if (externalUrl) formData.append('external_url', externalUrl);
    if (estimatedTime) formData.append('estimated_time', estimatedTime);
    if (image) formData.append('image', image);

    const bom = bomEntries.map((e) => ({
      component_id: e.component.id,
      quantity: e.quantity,
      notes: e.notes,
      is_optional: e.is_optional,
    }));
    formData.append('bom', JSON.stringify(bom));

    submitMutation.mutate(formData);
  };

  const canProceed = name.trim() && description.trim() && difficulty && category;

  if (submittedRecipe) {
    return (
      <div className="py-8">
        <div className="mx-auto max-w-3xl px-4">
          <div className="mb-8">
            <h1 className="font-display text-3xl font-bold text-white mb-2">
              {t('submit_recipe.title')}
            </h1>
          </div>
          <ModerationNotice
            itemLabel={submittedRecipe.name}
            viewLink={`/recipes/${submittedRecipe.id}`}
            onSubmitAnother={() => {
              setSubmittedRecipe(null);
              setStep(1);
              setName('');
              setDescription('');
              setDifficulty('beginner');
              setCategory('other');
              setExternalUrl('');
              setEstimatedTime('');
              setImage(null);
              setBomEntries([]);
              setError('');
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-3xl px-4">
        <h1 className="font-display text-3xl font-bold text-white mb-2">
          {t('submit_recipe.title')}
        </h1>
        <p className="text-gray-400 mb-8">
          {t('submit_recipe.subtitle')}
        </p>

        {/* Step indicator */}
        <div className="flex items-center gap-4 mb-8">
          <div
            className={clsx(
              'flex items-center gap-2 font-mono text-sm',
              step === 1 ? 'text-cyber-cyan' : 'text-gray-500'
            )}
          >
            <span
              className={clsx(
                'w-6 h-6 flex items-center justify-center border text-xs',
                step === 1 ? 'border-cyber-cyan' : 'border-gray-600'
              )}
            >
              1
            </span>
            {t('submit_recipe.step_details')}
          </div>
          <div className="flex-1 border-t border-cyber-light/30" />
          <div
            className={clsx(
              'flex items-center gap-2 font-mono text-sm',
              step === 2 ? 'text-cyber-cyan' : 'text-gray-500'
            )}
          >
            <span
              className={clsx(
                'w-6 h-6 flex items-center justify-center border text-xs',
                step === 2 ? 'border-cyber-cyan' : 'border-gray-600'
              )}
            >
              2
            </span>
            {t('submit_recipe.step_bom')}
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
            {error}
          </div>
        )}

        {/* Step 1: Recipe Details */}
        {step === 1 && (
          <div className="card-cyber p-6 space-y-4">
            <div>
              <label className="block text-sm font-mono text-gray-400 mb-1">
                {t('submit_recipe.name')} *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. DIY USB Power Bank"
                className="input-cyber"
                maxLength={200}
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-1">
                {t('submit_recipe.description')} *
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this recipe builds, how it works, and any important notes..."
                className="input-cyber min-h-[120px]"
                rows={5}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-mono text-gray-400 mb-1">
                  {t('submit_recipe.difficulty')} *
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="input-cyber"
                >
                  {DIFFICULTIES.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-mono text-gray-400 mb-1">
                  {t('submit_recipe.category')} *
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="input-cyber"
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
              <label className="block text-sm font-mono text-gray-400 mb-1">
                {t('submit_recipe.tutorial_url')}
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
              <label className="block text-sm font-mono text-gray-400 mb-1">
                {t('submit_recipe.estimated_build_time')}
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
              <label className="block text-sm font-mono text-gray-400 mb-1">
                Hero Image
              </label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                onChange={(e) => setImage(e.target.files?.[0] || null)}
                className="input-cyber text-sm"
              />
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => setStep(2)}
                disabled={!canProceed}
                className="btn-cyber flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('submit_recipe.next_add_parts')}
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: BOM Builder */}
        {step === 2 && (
          <div className="card-cyber p-6">
            <h2 className="font-display text-lg text-white mb-4">
              {t('submit_recipe.add_components_title')}
            </h2>

            {/* Component search */}
            <div className="flex gap-2 mb-4">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleSearch();
                    }
                  }}
                  placeholder={t('submit_recipe.bom_search_placeholder')}
                  className="input-cyber pl-10"
                />
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
              </div>
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className="btn-cyber px-4"
              >
                {isSearching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  t('common.search')
                )}
              </button>
            </div>

            {/* Search results */}
            {searchResults.length > 0 && (
              <div className="mb-6 border border-cyber-light/30 max-h-48 overflow-y-auto">
                {searchResults.map((comp) => (
                  <button
                    key={comp.id}
                    onClick={() => addComponent(comp)}
                    disabled={bomEntries.some((e) => e.component.id === comp.id)}
                    className={clsx(
                      'w-full px-3 py-2 flex items-center justify-between text-left hover:bg-cyber-light/10 border-b border-cyber-light/10 last:border-b-0',
                      bomEntries.some((e) => e.component.id === comp.id) &&
                        'opacity-40 cursor-not-allowed'
                    )}
                  >
                    <div>
                      <span className="text-sm text-cyber-cyan font-mono">
                        {comp.part_number}
                      </span>
                      <span className="text-sm text-gray-500 ml-2">
                        {comp.manufacturer}
                      </span>
                      {comp.primary_value && (
                        <span className="text-xs text-gray-400 ml-2">
                          ({comp.primary_value})
                        </span>
                      )}
                    </div>
                    <Plus className="h-4 w-4 text-cyber-cyan" />
                  </button>
                ))}
              </div>
            )}

            {/* BOM table */}
            {bomEntries.length > 0 && (
              <div className="mb-6 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-cyber-light/30">
                      <th className="text-left py-2 px-2 text-gray-500 font-mono text-xs">
                        {t('submit_recipe.col_part')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 font-mono text-xs">
                        {t('submit_recipe.col_manufacturer')}
                      </th>
                      <th className="text-center py-2 px-2 text-gray-500 font-mono text-xs w-20">
                        {t('submit_recipe.col_qty')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 font-mono text-xs">
                        {t('submit_recipe.col_notes')}
                      </th>
                      <th className="text-center py-2 px-2 text-gray-500 font-mono text-xs w-20">
                        {t('submit_recipe.col_optional')}
                      </th>
                      <th className="w-10" />
                    </tr>
                  </thead>
                  <tbody>
                    {bomEntries.map((entry, idx) => (
                      <tr
                        key={entry.component.id}
                        className="border-b border-cyber-light/10"
                      >
                        <td className="py-2 px-2 text-cyber-cyan font-mono">
                          {entry.component.part_number}
                        </td>
                        <td className="py-2 px-2 text-gray-400">
                          {entry.component.manufacturer}
                        </td>
                        <td className="py-2 px-2">
                          <input
                            type="number"
                            min={1}
                            value={entry.quantity}
                            onChange={(e) =>
                              updateEntry(idx, {
                                quantity: Math.max(1, parseInt(e.target.value) || 1),
                              })
                            }
                            className="input-cyber text-center w-16 py-1 text-xs"
                          />
                        </td>
                        <td className="py-2 px-2">
                          <input
                            type="text"
                            value={entry.notes}
                            onChange={(e) =>
                              updateEntry(idx, { notes: e.target.value })
                            }
                            placeholder="Notes..."
                            className="input-cyber py-1 text-xs"
                            maxLength={500}
                          />
                        </td>
                        <td className="py-2 px-2 text-center">
                          <input
                            type="checkbox"
                            checked={entry.is_optional}
                            onChange={(e) =>
                              updateEntry(idx, { is_optional: e.target.checked })
                            }
                            className="accent-cyber-cyan"
                          />
                        </td>
                        <td className="py-2 px-2">
                          <button
                            onClick={() => removeComponent(idx)}
                            className="text-cyber-pink hover:text-cyber-pink/80"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {bomEntries.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                {t('submit_recipe.bom_empty')}
              </div>
            )}

            <div className="flex justify-between pt-4 border-t border-cyber-light/20">
              <button
                onClick={() => setStep(1)}
                className="text-gray-400 hover:text-white flex items-center gap-1 text-sm"
              >
                <ArrowLeft className="h-4 w-4" />
                {t('common.back')}
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitMutation.isPending || bomEntries.length === 0}
                className="btn-cyber flex items-center gap-2 disabled:opacity-50"
              >
                {submitMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                {t('submit_recipe.submit')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
