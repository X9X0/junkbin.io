import { useQuery } from '@tanstack/react-query';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { products, schematics, recipes, components } from '../api/endpoints';
import { Package, FileText, Wrench, Cpu, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import type { Product, Schematic, Recipe, Component } from '../types';
import { useTranslation } from 'react-i18next';

type TabType = 'products' | 'schematics' | 'recipes' | 'components';

const TAB_ACTIVE_STYLES: Record<TabType, string> = {
  products: 'border-cyber-cyan text-cyber-cyan',
  schematics: 'border-cyber-yellow text-cyber-yellow',
  recipes: 'border-cyber-green text-cyber-green',
  components: 'border-cyber-pink text-cyber-pink',
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function MySubmissions() {
  const { t } = useTranslation();
  const { isAuthenticated, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const activeTab = (searchParams.get('type') as TabType) || 'products';

  const TABS: { key: TabType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { key: 'products', label: t('my_submissions.tab_products'), icon: Package },
    { key: 'schematics', label: t('my_submissions.tab_schematics'), icon: FileText },
    { key: 'recipes', label: t('my_submissions.tab_recipes'), icon: Wrench },
    { key: 'components', label: t('my_submissions.tab_components'), icon: Cpu },
  ];

  const setTab = (tab: TabType) => {
    const params = new URLSearchParams();
    params.set('type', tab);
    setSearchParams(params);
  };

  const { data: productData, isLoading: loadingProducts } = useQuery({
    queryKey: ['mySubmissions', 'products', user?.id],
    queryFn: () => products.list({ created_by: user!.id } as any),
    enabled: isAuthenticated && activeTab === 'products' && !!user,
  });

  const { data: schematicData, isLoading: loadingSchematics } = useQuery({
    queryKey: ['mySubmissions', 'schematics', user?.id],
    queryFn: () => schematics.list({ uploaded_by: user!.id }),
    enabled: isAuthenticated && activeTab === 'schematics' && !!user,
  });

  const { data: recipeData, isLoading: loadingRecipes } = useQuery({
    queryKey: ['mySubmissions', 'recipes', user?.id],
    queryFn: () => recipes.list({ created_by: user!.id }),
    enabled: isAuthenticated && activeTab === 'recipes' && !!user,
  });

  const { data: componentData, isLoading: loadingComponents } = useQuery({
    queryKey: ['mySubmissions', 'components', user?.id],
    queryFn: () => components.list({ created_by: user!.id }),
    enabled: isAuthenticated && activeTab === 'components' && !!user,
  });

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const isLoading =
    (activeTab === 'products' && loadingProducts) ||
    (activeTab === 'schematics' && loadingSchematics) ||
    (activeTab === 'recipes' && loadingRecipes) ||
    (activeTab === 'components' && loadingComponents);

  return (
    <div className="py-8">
      <div className="mx-auto max-w-5xl px-4">
        {/* Header */}
        <div className="mb-6">
          <h1 className="font-display text-3xl font-bold text-white">
            MY <span className="text-cyber-cyan">SUBMISSIONS</span>
          </h1>
          <p className="text-gray-400 font-mono text-sm mt-1">
            {t('my_submissions.subtitle')}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-cyber-light/30 mb-6">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={clsx(
                'px-4 py-3 font-mono text-sm border-b-2 transition-colors flex items-center gap-2',
                activeTab === key
                  ? TAB_ACTIVE_STYLES[key]
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-cyber-cyan" />
          </div>
        ) : activeTab === 'products' ? (
          <ProductsList items={productData?.results || []} />
        ) : activeTab === 'schematics' ? (
          <SchematicsList items={schematicData?.results || []} />
        ) : activeTab === 'recipes' ? (
          <RecipesList items={recipeData?.results || []} />
        ) : (
          <ComponentsList items={componentData?.results || []} />
        )}
      </div>
    </div>
  );
}

function StatusBadge({ approved }: { approved: boolean }) {
  const { t } = useTranslation();
  return (
    <span
      className={clsx(
        'px-2 py-0.5 text-[10px] font-mono border',
        approved
          ? 'border-cyber-green/50 text-cyber-green'
          : 'border-cyber-yellow/50 text-cyber-yellow'
      )}
    >
      {approved ? t('common.approved') : t('common.pending')}
    </span>
  );
}

function EmptyState({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <div className="card-cyber p-12 text-center">
      <Package className="h-14 w-14 text-gray-600 mx-auto mb-4" />
      <h3 className="font-display text-lg text-white mb-2">{t(titleKey)}</h3>
    </div>
  );
}

function ProductsList({ items }: { items: Product[] }) {
  const { t } = useTranslation();
  if (items.length === 0) return <EmptyState titleKey="my_submissions.no_products" />;

  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-500 font-mono mb-4">{items.length} products</div>
      {items.map((product) => (
        <Link
          key={product.id}
          to={`/products/${product.id}`}
          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-cyan/50 transition-all block"
        >
          <div className="w-10 h-10 bg-cyber-dark border border-cyber-light/20 flex items-center justify-center flex-shrink-0">
            <Package className="h-5 w-5 text-cyber-cyan" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-mono text-cyber-cyan">{product.manufacturer}</span>
              <StatusBadge approved={product.is_approved} />
            </div>
            <h3 className="text-white font-semibold truncate">{product.model_number}</h3>
          </div>
          <div className="text-xs text-gray-500 font-mono flex-shrink-0 hidden sm:block">
            {formatDate(product.created_at)}
          </div>
        </Link>
      ))}
    </div>
  );
}

function SchematicsList({ items }: { items: Schematic[] }) {
  const { t } = useTranslation();
  if (items.length === 0) return <EmptyState titleKey="my_submissions.no_schematics" />;

  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-500 font-mono mb-4">{items.length} schematics</div>
      {items.map((schematic) => (
        <Link
          key={schematic.id}
          to={`/products/${schematic.product}`}
          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-yellow/50 transition-all block"
        >
          <div className="w-10 h-10 bg-cyber-dark border border-cyber-light/20 flex items-center justify-center flex-shrink-0">
            <FileText className="h-5 w-5 text-cyber-yellow" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-mono text-cyber-yellow">
                {schematic.schematic_type_display || schematic.schematic_type}
              </span>
              <StatusBadge approved={schematic.is_approved} />
            </div>
            <h3 className="text-white font-semibold truncate">{schematic.title}</h3>
          </div>
          <div className="text-xs text-gray-500 font-mono flex-shrink-0 hidden sm:block">
            {formatDate(schematic.uploaded_at)}
          </div>
        </Link>
      ))}
    </div>
  );
}

function RecipesList({ items }: { items: Recipe[] }) {
  const { t } = useTranslation();
  if (items.length === 0) return <EmptyState titleKey="my_submissions.no_recipes" />;

  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-500 font-mono mb-4">{items.length} recipes</div>
      {items.map((recipe) => (
        <Link
          key={recipe.id}
          to={`/recipes/${recipe.id}`}
          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-green/50 transition-all block"
        >
          <div className="w-10 h-10 bg-cyber-dark border border-cyber-light/20 flex items-center justify-center flex-shrink-0">
            <Wrench className="h-5 w-5 text-cyber-green" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-mono text-cyber-green">
                {recipe.category_display || recipe.category}
              </span>
              <StatusBadge approved={recipe.is_approved} />
            </div>
            <h3 className="text-white font-semibold truncate">{recipe.name}</h3>
          </div>
          <div className="text-xs text-gray-500 font-mono flex-shrink-0 hidden sm:block">
            {formatDate(recipe.created_at)}
          </div>
        </Link>
      ))}
    </div>
  );
}

function ComponentsList({ items }: { items: Component[] }) {
  const { t } = useTranslation();
  if (items.length === 0) return <EmptyState titleKey="my_submissions.no_components" />;

  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-500 font-mono mb-4">{items.length} components</div>
      {items.map((component) => (
        <Link
          key={component.id}
          to={`/components/${component.id}/products`}
          className="card-cyber p-4 flex items-center gap-4 hover:border-cyber-pink/50 transition-all block"
        >
          <div className="w-10 h-10 bg-cyber-dark border border-cyber-light/20 flex items-center justify-center flex-shrink-0">
            <Cpu className="h-5 w-5 text-cyber-pink" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-mono text-cyber-pink">{component.manufacturer}</span>
              <span className="text-xs font-mono text-gray-500">
                {component.component_type_display || component.component_type}
              </span>
            </div>
            <h3 className="text-white font-semibold truncate">{component.part_number}</h3>
          </div>
          <div className="text-xs text-gray-500 font-mono flex-shrink-0 hidden sm:block">
            {component.usage_count} uses
          </div>
        </Link>
      ))}
    </div>
  );
}
