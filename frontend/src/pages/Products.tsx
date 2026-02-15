import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { Cpu, Grid, List, Search, ChevronDown } from 'lucide-react';
import clsx from 'clsx';
import Pagination from '../components/Pagination';
import { ProductGridSkeleton } from '../components/Skeleton';
import LazyImage from '../components/LazyImage';

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'router', label: 'Router' },
  { value: 'phone', label: 'Smartphone' },
  { value: 'laptop', label: 'Laptop' },
  { value: 'tv', label: 'Television' },
  { value: 'gaming', label: 'Gaming Console' },
  { value: 'remote', label: 'Remote Control' },
  { value: 'iot', label: 'IoT Device' },
  { value: 'audio', label: 'Audio Equipment' },
  { value: 'other', label: 'Other' },
];

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const search = searchParams.get('search') || '';
  const category = searchParams.get('category') || '';
  const ordering = searchParams.get('ordering') || '-created_at';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading } = useQuery({
    queryKey: ['products', { search, category, ordering, page }],
    queryFn: () => products.list({ search, category, ordering, page }),
  });

  const pageSize = 20; // Default page size from backend
  const totalPages = data ? Math.ceil(data.count / pageSize) : 0;

  const updateFilter = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    // Reset to page 1 when filters change
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
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            PRODUCT <span className="text-cyber-cyan">DATABASE</span>
          </h1>
          <p className="text-gray-400">
            Browse documented electronic products and their components
          </p>
        </div>

        {/* Filters Bar */}
        <div className="card-cyber p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <input
                type="text"
                value={search}
                onChange={(e) => updateFilter('search', e.target.value)}
                placeholder="Search by manufacturer, model, FCC ID..."
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
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
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
                <option value="-created_at">Newest First</option>
                <option value="created_at">Oldest First</option>
                <option value="manufacturer">Manufacturer A-Z</option>
                <option value="-component_count">Most Components</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>

            {/* View Mode */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('grid')}
                className={clsx(
                  'p-2 border transition-colors',
                  viewMode === 'grid'
                    ? 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10'
                    : 'border-cyber-light/50 text-gray-500 hover:text-white'
                )}
              >
                <Grid className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={clsx(
                  'p-2 border transition-colors',
                  viewMode === 'list'
                    ? 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10'
                    : 'border-cyber-light/50 text-gray-500 hover:text-white'
                )}
              >
                <List className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Results count */}
        {data && (
          <div className="mb-4 text-sm text-gray-500 font-mono">
            {data.count} products found
          </div>
        )}

        {/* Loading state */}
        {isLoading && <ProductGridSkeleton count={8} />}

        {/* Products Grid */}
        {data && !isLoading && (
          <div
            className={clsx(
              viewMode === 'grid'
                ? 'grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                : 'flex flex-col gap-4'
            )}
          >
            {data.results.map((product) => (
              <Link
                key={product.id}
                to={`/products/${product.id}`}
                className={clsx(
                  'card-cyber hover:border-cyber-cyan/50 transition-all group',
                  viewMode === 'grid' ? 'p-4' : 'p-4 flex gap-4'
                )}
              >
                {/* Image */}
                <div
                  className={clsx(
                    'bg-cyber-black flex items-center justify-center border border-cyber-light/20',
                    viewMode === 'grid' ? 'aspect-video mb-4' : 'w-24 h-24 flex-shrink-0'
                  )}
                >
                  {product.primary_image ? (
                    <LazyImage
                      src={product.primary_image.thumbnail || product.primary_image.image}
                      alt={product.model_number}
                      className="w-full h-full object-cover bg-cyber-black"
                      fallback={<Cpu className="h-8 w-8 text-gray-600" />}
                    />
                  ) : (
                    <Cpu className="h-8 w-8 text-gray-600" />
                  )}
                </div>

                {/* Info */}
                <div className={viewMode === 'list' ? 'flex-1 min-w-0' : ''}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-cyber-cyan">
                      {product.manufacturer}
                    </span>
                    {product.is_featured && (
                      <span className="badge-cyber text-cyber-yellow border-cyber-yellow text-[10px]">
                        FEATURED
                      </span>
                    )}
                  </div>

                  <h3 className="font-semibold text-white group-hover:text-cyber-cyan transition-colors truncate">
                    {product.model_number}
                  </h3>

                  {product.revision && (
                    <div className="text-xs text-gray-500 font-mono">
                      Rev: {product.revision}
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-gray-500">
                    <span className="badge-cyber text-gray-400 border-gray-600">
                      {product.category_display || product.category}
                    </span>
                    <span>{product.component_count} parts</span>
                    {product.fcc_id && <span>FCC: {product.fcc_id}</span>}
                  </div>

                  {viewMode === 'list' && product.description && (
                    <p className="mt-2 text-sm text-gray-400 line-clamp-2">
                      {product.description}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Empty state */}
        {data && data.results.length === 0 && (
          <div className="text-center py-20">
            <Cpu className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="font-display text-xl text-white mb-2">NO PRODUCTS FOUND</h3>
            <p className="text-gray-500 mb-6">
              Try adjusting your search or filters
            </p>
            <Link to="/submit" className="btn-cyber">
              ADD A PRODUCT
            </Link>
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
