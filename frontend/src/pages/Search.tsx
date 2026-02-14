import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { search } from '../api/endpoints';
import {
  Search as SearchIcon,
  Package,
  Cpu,
  FileText,
  ExternalLink,
  Loader2,
  User as UserIcon,
  Shield,
  Award,
} from 'lucide-react';
import clsx from 'clsx';
import { useState, useEffect } from 'react';

interface SearchResult {
  products: Array<{
    id: string;
    manufacturer: string;
    model_number: string;
    category: string;
    category_display?: string;
    primary_image?: { thumbnail?: string };
  }>;
  components: Array<{
    id: string;
    part_number: string;
    manufacturer: string;
    component_type: string;
    component_type_display?: string;
    package_type?: string;
    primary_value?: string;
  }>;
  schematics: Array<{
    id: string;
    title: string;
    schematic_type: string;
    schematic_type_display?: string;
    product: { id: string; manufacturer: string; model_number: string };
  }>;
  users: Array<{
    id: string;
    username: string;
    display_name?: string;
    avatar?: string;
    reputation_score: number;
    is_trusted: boolean;
  }>;
}

type TabType = 'all' | 'products' | 'components' | 'schematics' | 'users';

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const [localQuery, setLocalQuery] = useState(query);
  const [activeTab, setActiveTab] = useState<TabType>('all');

  useEffect(() => {
    setLocalQuery(query);
  }, [query]);

  const { data, isLoading, error } = useQuery<SearchResult>({
    queryKey: ['search', query],
    queryFn: () => search.global(query),
    enabled: query.length >= 2,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (localQuery.trim()) {
      setSearchParams({ q: localQuery.trim() });
    }
  };

  const totalResults = data
    ? data.products.length + data.components.length + data.schematics.length + (data.users?.length || 0)
    : 0;

  const tabs = [
    { key: 'all', label: 'All', count: totalResults },
    { key: 'products', label: 'Products', count: data?.products.length || 0, icon: Package },
    { key: 'components', label: 'Components', count: data?.components.length || 0, icon: Cpu },
    { key: 'schematics', label: 'Schematics', count: data?.schematics.length || 0, icon: FileText },
    { key: 'users', label: 'Users', count: data?.users?.length || 0, icon: UserIcon },
  ];

  return (
    <div className="py-8">
      <div className="mx-auto max-w-5xl px-4">
        {/* Search Header */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-6">
            <span className="text-cyber-cyan">SEARCH</span> DATABASE
          </h1>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={localQuery}
                onChange={(e) => setLocalQuery(e.target.value)}
                placeholder="Search products, components..."
                className="w-full bg-cyber-dark border-2 border-cyber-light/50 px-5 py-3 sm:py-4 pl-12 sm:pl-14 text-base sm:text-lg font-mono text-gray-200 placeholder-gray-500 focus:border-cyber-cyan focus:outline-none transition-colors"
              />
              <SearchIcon className="absolute left-4 sm:left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
            </div>
            <button
              type="submit"
              className="btn-cyber py-3 sm:py-2 w-full sm:w-auto"
            >
              SEARCH
            </button>
          </form>
        </div>

        {/* Results */}
        {query.length < 2 ? (
          <div className="card-cyber p-12 text-center">
            <SearchIcon className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 font-mono">
              Enter at least 2 characters to search
            </p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 text-cyber-cyan animate-spin mr-3" />
            <span className="text-gray-400 font-mono">Searching...</span>
          </div>
        ) : error ? (
          <div className="card-cyber p-8 text-center">
            <p className="text-cyber-pink font-mono">Error performing search</p>
          </div>
        ) : totalResults === 0 ? (
          <div className="card-cyber p-12 text-center">
            <SearchIcon className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 font-mono mb-2">No results found for "{query}"</p>
            <p className="text-gray-600 text-sm">Try different keywords or check your spelling</p>
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="mb-6">
              <p className="text-gray-400 font-mono text-sm">
                Found <span className="text-cyber-cyan">{totalResults}</span> results for "
                <span className="text-white">{query}</span>"
              </p>
            </div>

            {/* Tabs */}
            <div className="border-b border-cyber-light/30 mb-6">
              <div className="flex gap-6 overflow-x-auto">
                {tabs.map(({ key, label, count, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key as TabType)}
                    className={clsx(
                      'flex items-center gap-2 py-3 border-b-2 font-mono text-sm whitespace-nowrap transition-colors',
                      activeTab === key
                        ? 'border-cyber-cyan text-cyber-cyan'
                        : 'border-transparent text-gray-500 hover:text-white'
                    )}
                  >
                    {Icon && <Icon className="h-4 w-4" />}
                    {label}
                    <span
                      className={clsx(
                        'px-1.5 py-0.5 text-xs',
                        activeTab === key
                          ? 'bg-cyber-cyan/20 text-cyber-cyan'
                          : 'bg-cyber-light/30 text-gray-500'
                      )}
                    >
                      {count}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Results List */}
            <div className="space-y-8">
              {/* Products */}
              {(activeTab === 'all' || activeTab === 'products') &&
                data?.products &&
                data.products.length > 0 && (
                  <div>
                    {activeTab === 'all' && (
                      <h2 className="font-display text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Package className="h-5 w-5 text-cyber-cyan" />
                        PRODUCTS ({data.products.length})
                      </h2>
                    )}
                    <div className="grid gap-3">
                      {data.products.map((product) => (
                        <Link
                          key={product.id}
                          to={`/products/${product.id}`}
                          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-cyan/50 transition-all group"
                        >
                          <div className="w-16 h-16 bg-cyber-black flex items-center justify-center flex-shrink-0">
                            {product.primary_image?.thumbnail ? (
                              <img
                                src={product.primary_image.thumbnail}
                                alt=""
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <Package className="h-8 w-8 text-gray-600" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-cyber-cyan font-mono text-xs mb-1">
                              {product.manufacturer}
                            </div>
                            <h3 className="font-semibold text-white group-hover:text-cyber-cyan transition-colors truncate">
                              {product.model_number}
                            </h3>
                            <span className="badge-cyber text-gray-400 border-gray-600 text-[10px] mt-1">
                              {product.category_display || product.category}
                            </span>
                          </div>
                          <ExternalLink className="h-4 w-4 text-gray-600 group-hover:text-cyber-cyan transition-colors" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

              {/* Components */}
              {(activeTab === 'all' || activeTab === 'components') &&
                data?.components &&
                data.components.length > 0 && (
                  <div>
                    {activeTab === 'all' && (
                      <h2 className="font-display text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Cpu className="h-5 w-5 text-cyber-pink" />
                        COMPONENTS ({data.components.length})
                      </h2>
                    )}
                    <div className="grid gap-3">
                      {data.components.map((component) => (
                        <Link
                          key={component.id}
                          to={`/components/${component.id}/products`}
                          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-pink/50 transition-all group"
                        >
                          <div className="w-16 h-16 bg-cyber-black flex items-center justify-center flex-shrink-0 border border-cyber-pink/30">
                            <Cpu className="h-8 w-8 text-cyber-pink/50" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-mono font-semibold text-white group-hover:text-cyber-pink transition-colors">
                              {component.part_number}
                            </h3>
                            <div className="text-gray-400 text-sm">{component.manufacturer}</div>
                            <div className="flex flex-wrap items-center gap-2 mt-1">
                              <span className="badge-cyber text-cyber-pink border-cyber-pink/50 text-[10px]">
                                {component.component_type_display || component.component_type}
                              </span>
                              {component.package_type && (
                                <span className="badge-cyber text-gray-400 border-gray-600 text-[10px]">
                                  {component.package_type}
                                </span>
                              )}
                              {component.primary_value && (
                                <span className="font-mono text-sm text-cyber-yellow">
                                  {component.primary_value}
                                </span>
                              )}
                            </div>
                          </div>
                          <ExternalLink className="h-4 w-4 text-gray-600 group-hover:text-cyber-pink transition-colors" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

              {/* Schematics */}
              {(activeTab === 'all' || activeTab === 'schematics') &&
                data?.schematics &&
                data.schematics.length > 0 && (
                  <div>
                    {activeTab === 'all' && (
                      <h2 className="font-display text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <FileText className="h-5 w-5 text-cyber-green" />
                        SCHEMATICS ({data.schematics.length})
                      </h2>
                    )}
                    <div className="grid gap-3">
                      {data.schematics.map((schematic) => (
                        <Link
                          key={schematic.id}
                          to={`/products/${schematic.product.id}`}
                          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-green/50 transition-all group"
                        >
                          <div className="w-16 h-16 bg-cyber-black flex items-center justify-center flex-shrink-0 border border-cyber-green/30">
                            <FileText className="h-8 w-8 text-cyber-green/50" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-white group-hover:text-cyber-green transition-colors truncate">
                              {schematic.title}
                            </h3>
                            <div className="text-gray-400 text-sm">
                              {schematic.product.manufacturer} {schematic.product.model_number}
                            </div>
                            <span className="badge-cyber text-cyber-green border-cyber-green/50 text-[10px] mt-1">
                              {schematic.schematic_type_display || schematic.schematic_type}
                            </span>
                          </div>
                          <ExternalLink className="h-4 w-4 text-gray-600 group-hover:text-cyber-green transition-colors" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

              {/* Users */}
              {(activeTab === 'all' || activeTab === 'users') &&
                data?.users &&
                data.users.length > 0 && (
                  <div>
                    {activeTab === 'all' && (
                      <h2 className="font-display text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <UserIcon className="h-5 w-5 text-cyber-yellow" />
                        USERS ({data.users.length})
                      </h2>
                    )}
                    <div className="grid gap-3">
                      {data.users.map((user) => (
                        <Link
                          key={user.id}
                          to={`/users/${user.id}`}
                          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-yellow/50 transition-all group"
                        >
                          <div className="w-16 h-16 bg-cyber-black flex items-center justify-center flex-shrink-0 border border-cyber-yellow/30">
                            {user.avatar ? (
                              <img src={user.avatar} alt="" className="w-full h-full object-cover" />
                            ) : (
                              <UserIcon className="h-8 w-8 text-cyber-yellow/50" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-mono font-semibold text-white group-hover:text-cyber-yellow transition-colors">
                              {user.display_name || user.username}
                            </h3>
                            {user.display_name && user.display_name !== user.username && (
                              <div className="text-gray-500 text-xs font-mono">@{user.username}</div>
                            )}
                            <div className="flex items-center gap-2 mt-1">
                              <span className="flex items-center gap-1 text-cyber-cyan font-mono text-xs">
                                <Award className="h-3 w-3" />
                                {user.reputation_score} rep
                              </span>
                              {user.is_trusted && (
                                <span className="flex items-center gap-1 text-cyber-green font-mono text-xs">
                                  <Shield className="h-3 w-3" />
                                  TRUSTED
                                </span>
                              )}
                            </div>
                          </div>
                          <ExternalLink className="h-4 w-4 text-gray-600 group-hover:text-cyber-yellow transition-colors" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
