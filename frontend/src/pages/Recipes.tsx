import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { recipes } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { Search, ChevronDown, Cpu } from 'lucide-react';
import Pagination from '../components/Pagination';
import RecipeCard from '../components/RecipeCard';
import { Link } from 'react-router-dom';
import { RECIPE_CATEGORIES, DIFFICULTIES } from '../utils/constants';
import { useTranslation } from 'react-i18next';

export default function Recipes() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth();

  const FALLBACK_CATEGORIES = [
    { value: '', label: t('recipes.all_categories') },
    ...RECIPE_CATEGORIES,
  ];

  const FILTER_DIFFICULTIES = [
    { value: '', label: t('recipes.all_difficulties') },
    ...DIFFICULTIES,
  ];

  const q = searchParams.get('q') || '';
  const category = searchParams.get('category') || '';
  const difficulty = searchParams.get('difficulty') || '';
  const ordering = searchParams.get('ordering') || '-created_at';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data: apiCategories } = useQuery({
    queryKey: ['recipe-categories'],
    queryFn: recipes.categories,
    staleTime: 5 * 60 * 1000,
  });

  const categoryOptions = apiCategories
    ? [{ value: '', label: t('recipes.all_categories') }, ...apiCategories.map((c) => ({ value: c.value, label: c.label }))]
    : FALLBACK_CATEGORIES;

  const { data, isLoading } = useQuery({
    queryKey: ['recipes', { q, category, difficulty, ordering, page }],
    queryFn: () => recipes.list({ q, category, difficulty, ordering, page }),
  });

  const pageSize = 20;
  const totalPages = data ? Math.ceil(data.count / pageSize) : 0;

  const updateFilter = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    if (key !== 'page') {
      newParams.delete('page');
    }
    setSearchParams(newParams);
  };

  const goToPage = (newPage: number) => {
    const newParams = new URLSearchParams(searchParams);
    if (newPage > 1) {
      newParams.set('page', String(newPage));
    } else {
      newParams.delete('page');
    }
    setSearchParams(newParams);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="py-8">
      <div className="mx-auto max-w-screen-2xl px-4">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold text-white mb-2">
              {t('recipes.title')}
            </h1>
            <p className="text-gray-400">
              {t('recipes.subtitle')}
            </p>
          </div>
          {isAuthenticated && (
            <Link to="/recipes/submit" className="btn-cyber text-sm">
              {t('recipes.submit_btn')}
            </Link>
          )}
        </div>

        {/* Filters Bar */}
        <div className="card-cyber p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <input
                type="text"
                value={q}
                onChange={(e) => updateFilter('q', e.target.value)}
                placeholder={t('recipes.search_placeholder')}
                className="input-cyber pl-10"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
            </div>

            {/* Category */}
            <div className="relative">
              <select
                value={category}
                onChange={(e) => updateFilter('category', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full lg:w-48"
              >
                {categoryOptions.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>

            {/* Difficulty */}
            <div className="relative">
              <select
                value={difficulty}
                onChange={(e) => updateFilter('difficulty', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full lg:w-48"
              >
                {FILTER_DIFFICULTIES.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>

            {/* Sort */}
            <div className="relative">
              <select
                value={ordering}
                onChange={(e) => updateFilter('ordering', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full lg:w-48"
              >
                <option value="-created_at">{t('recipes.newest_first')}</option>
                <option value="created_at">{t('recipes.oldest_first')}</option>
                <option value="-view_count">{t('recipes.most_viewed')}</option>
                <option value="name">{t('recipes.name_az')}</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Results count */}
        {data && (
          <div className="mb-4 text-sm text-gray-500 font-mono">
            {t('recipes.count_found', { count: data.count })}
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-cyber-cyan font-mono animate-pulse">
              {t('recipes.loading')}
            </div>
          </div>
        )}

        {/* Recipes Grid */}
        {data && !isLoading && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {data.results.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                showMatch={isAuthenticated}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {data && data.results.length === 0 && (
          <div className="text-center py-20">
            <Cpu className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="font-display text-xl text-white mb-2">{t('recipes.no_recipes_title')}</h3>
            <p className="text-gray-500 mb-6">
              {t('recipes.no_recipes_desc')}
            </p>
            {isAuthenticated && (
              <Link to="/recipes/submit" className="btn-cyber">
                {t('recipes.submit_a_recipe')}
              </Link>
            )}
          </div>
        )}

        {/* Pagination */}
        {data && totalPages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={goToPage}
            color="cyan"
            className="mt-8"
          />
        )}
      </div>
    </div>
  );
}
