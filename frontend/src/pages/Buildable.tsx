import { useSearchParams, Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { recipes } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { ChevronDown, Hammer, Archive } from 'lucide-react';
import Pagination from '../components/Pagination';
import RecipeCard from '../components/RecipeCard';
import { RECIPE_CATEGORIES, DIFFICULTIES } from '../utils/constants';

const FALLBACK_CATEGORIES = [
  { value: '', label: 'All Categories' },
  ...RECIPE_CATEGORIES,
];

const FILTER_DIFFICULTIES = [
  { value: '', label: 'All Difficulties' },
  ...DIFFICULTIES,
];

export default function Buildable() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const category = searchParams.get('category') || '';
  const difficulty = searchParams.get('difficulty') || '';
  const minMatch = searchParams.get('min_match') || '0';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data: apiCategories } = useQuery({
    queryKey: ['recipe-categories'],
    queryFn: recipes.categories,
    staleTime: 5 * 60 * 1000,
  });

  const categoryOptions = apiCategories
    ? [{ value: '', label: 'All Categories' }, ...apiCategories.map((c) => ({ value: c.value, label: c.label }))]
    : FALLBACK_CATEGORIES;

  const { data, isLoading } = useQuery({
    queryKey: ['buildable', { category, difficulty, min_match: minMatch, page }],
    queryFn: () =>
      recipes.buildable({ category, difficulty, min_match: minMatch, page }),
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
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2 flex items-center gap-3">
            <Hammer className="h-8 w-8 text-cyber-green" />
            {t('buildable.title')}
          </h1>
          <p className="text-gray-400">
            {t('buildable.subtitle')}
          </p>
        </div>

        {/* Filters */}
        <div className="card-cyber p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Category */}
            <div className="relative flex-1">
              <select
                value={category}
                onChange={(e) => updateFilter('category', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full"
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
            <div className="relative flex-1">
              <select
                value={difficulty}
                onChange={(e) => updateFilter('difficulty', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full"
              >
                {FILTER_DIFFICULTIES.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>

            {/* Min match */}
            <div className="relative flex-1">
              <select
                value={minMatch}
                onChange={(e) => updateFilter('min_match', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full"
              >
                <option value="0">{t('buildable.filter_any')}</option>
                <option value="25">{t('buildable.filter_25')}</option>
                <option value="50">{t('buildable.filter_50')}</option>
                <option value="75">{t('buildable.filter_75')}</option>
                <option value="100">{t('buildable.filter_100')}</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Results count */}
        {data && (
          <div className="mb-4 text-sm text-gray-500 font-mono">
            {t('buildable.count_found', { count: data.count })}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-cyber-green font-mono animate-pulse">
              {t('buildable.loading')}
            </div>
          </div>
        )}

        {/* Results Grid */}
        {data && !isLoading && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {data.results.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} showMatch />
            ))}
          </div>
        )}

        {/* Empty state */}
        {data && data.results.length === 0 && (
          <div className="text-center py-20">
            <Hammer className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="font-display text-xl text-white mb-2">
              {t('buildable.no_recipes_title')}
            </h3>
            <p className="text-gray-500 mb-6">
              {t('buildable.no_recipes_desc')}
            </p>
            <Link
              to="/my-junkbin"
              className="btn-cyber inline-flex items-center gap-2"
            >
              <Archive className="h-4 w-4" />
              {t('my_junkbin.title')}
            </Link>
          </div>
        )}

        {/* Pagination */}
        {data && totalPages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={goToPage}
            color="green"
            className="mt-8"
          />
        )}
      </div>
    </div>
  );
}
