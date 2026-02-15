import { useSearchParams, Link, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { recipes } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { ChevronDown, Hammer, Archive } from 'lucide-react';
import Pagination from '../components/Pagination';
import RecipeCard from '../components/RecipeCard';

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'audio', label: 'Audio' },
  { value: 'power_supply', label: 'Power Supply' },
  { value: 'iot', label: 'IoT' },
  { value: 'repair', label: 'Repair' },
  { value: 'lighting', label: 'Lighting' },
  { value: 'test_equipment', label: 'Test Equipment' },
  { value: 'radio', label: 'Radio' },
  { value: 'computing', label: 'Computing' },
  { value: 'robotics', label: 'Robotics' },
  { value: 'wearable', label: 'Wearable' },
  { value: 'other', label: 'Other' },
];

const DIFFICULTIES = [
  { value: '', label: 'All Difficulties' },
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'expert', label: 'Expert' },
];

export default function Buildable() {
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const category = searchParams.get('category') || '';
  const difficulty = searchParams.get('difficulty') || '';
  const minMatch = searchParams.get('min_match') || '0';
  const page = parseInt(searchParams.get('page') || '1', 10);

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
      <div className="mx-auto max-w-7xl px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2 flex items-center gap-3">
            <Hammer className="h-8 w-8 text-cyber-green" />
            WHAT CAN I <span className="text-cyber-green">BUILD?</span>
          </h1>
          <p className="text-gray-400">
            Recipes matched against your junkbin — sorted by how many parts you already have
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
                {CATEGORIES.map((cat) => (
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
                {DIFFICULTIES.map((d) => (
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
                <option value="0">Any Match %</option>
                <option value="25">25%+ Match</option>
                <option value="50">50%+ Match</option>
                <option value="75">75%+ Match</option>
                <option value="100">100% Match</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Results count */}
        {data && (
          <div className="mb-4 text-sm text-gray-500 font-mono">
            {data.count} buildable recipes
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-cyber-green font-mono animate-pulse">
              MATCHING YOUR PARTS...
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
              NO MATCHING RECIPES
            </h3>
            <p className="text-gray-500 mb-6">
              Add more components to your junkbin to find matching recipes
            </p>
            <Link
              to="/my-junkbin"
              className="btn-cyber inline-flex items-center gap-2"
            >
              <Archive className="h-4 w-4" />
              GO TO MY JUNKBIN
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
