import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { schematics, products as productsApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import SchematicUpload from '../components/SchematicUpload';
import {
  FileText,
  Grid,
  List,
  Search,
  ChevronDown,
  Download,
  ExternalLink,
  CheckCircle,
  FileIcon,
  BookOpen,
  Cpu,
  Layout,
  Zap,
  Cable,
  ClipboardList,
  Upload,
  ArrowLeft,
  X,
} from 'lucide-react';
import clsx from 'clsx';
import Pagination from '../components/Pagination';
import { Skeleton } from '../components/Skeleton';

const SCHEMATIC_TYPES = [
  { value: '', label: 'All Types', icon: FileText },
  { value: 'full_schematic', label: 'Full Schematic', icon: Zap },
  { value: 'block_diagram', label: 'Block Diagram', icon: Layout },
  { value: 'pcb_layout', label: 'PCB Layout', icon: Cpu },
  { value: 'service_manual', label: 'Service Manual', icon: BookOpen },
  { value: 'datasheet', label: 'Datasheet', icon: FileIcon },
  { value: 'pinout', label: 'Pinout Diagram', icon: Cable },
  { value: 'wiring_diagram', label: 'Wiring Diagram', icon: Cable },
  { value: 'bom', label: 'Bill of Materials', icon: ClipboardList },
  { value: 'other', label: 'Other', icon: FileText },
];

const SOURCE_TYPES = [
  { value: '', label: 'All Sources' },
  { value: 'official', label: 'Official/Manufacturer' },
  { value: 'community', label: 'Community' },
  { value: 'reverse_engineered', label: 'Reverse Engineered' },
  { value: 'fcc_filing', label: 'FCC Filing' },
  { value: 'leaked', label: 'Leaked' },
];

function formatFileSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileTypeIcon(fileType: string) {
  if (fileType === 'pdf') return '📄';
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileType)) return '🖼️';
  if (['zip', 'rar', '7z'].includes(fileType)) return '📦';
  return '📎';
}

export default function Schematics() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [contributeOpen, setContributeOpen] = useState(false);
  const [productSearch, setProductSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<{ id: string; label: string } | null>(null);

  const { isAuthenticated } = useAuth();

  const { data: productSearchResults } = useQuery({
    queryKey: ['productSearch', productSearch],
    queryFn: () => productsApi.list({ search: productSearch, page_size: 8 }),
    enabled: productSearch.length >= 2,
    staleTime: 30000,
  });

  const search = searchParams.get('search') || '';
  const schematicType = searchParams.get('schematic_type') || '';
  const sourceType = searchParams.get('source_type') || '';
  const ordering = searchParams.get('ordering') || '-download_count';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading } = useQuery({
    queryKey: ['schematics', { search, schematic_type: schematicType, source_type: sourceType, ordering, page }],
    queryFn: () => schematics.list({ search, schematic_type: schematicType, source_type: sourceType, ordering, page }),
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
        <div className="mb-8 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-white mb-2">
              SCHEMATICS & <span className="text-cyber-green">DOCUMENTATION</span>
            </h1>
            <p className="text-gray-400">
              Service manuals, block diagrams, PCB layouts, and technical documentation
            </p>
          </div>
          <button
            onClick={() => { setContributeOpen((v) => !v); setSelectedProduct(null); setProductSearch(''); }}
            className="flex-shrink-0 flex items-center gap-2 btn-cyber btn-cyber-green text-sm"
          >
            <Upload className="h-4 w-4" />
            CONTRIBUTE
          </button>
        </div>

        {/* Contribute Panel */}
        {contributeOpen && (
          <div className="card-cyber p-6 mb-6 border-cyber-green/30">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg text-white">
                CONTRIBUTE A DOCUMENT
              </h2>
              <button onClick={() => setContributeOpen(false)} className="text-gray-500 hover:text-white transition-colors p-1">
                <X className="h-5 w-5" />
              </button>
            </div>

            {!isAuthenticated ? (
              <div className="text-center py-8">
                <p className="text-gray-400 mb-4">You must be logged in to contribute documents.</p>
                <a href="/login" className="btn-cyber">LOGIN TO CONTRIBUTE</a>
              </div>
            ) : selectedProduct ? (
              <div>
                <div className="flex items-center gap-3 mb-6 p-3 border border-cyber-green/30 bg-cyber-green/5">
                  <Cpu className="h-4 w-4 text-cyber-green flex-shrink-0" />
                  <span className="text-white font-mono text-sm flex-1 truncate">{selectedProduct.label}</span>
                  <button
                    onClick={() => { setSelectedProduct(null); setProductSearch(''); }}
                    className="text-xs font-mono text-gray-500 hover:text-cyber-cyan flex items-center gap-1 flex-shrink-0 transition-colors"
                  >
                    <ArrowLeft className="h-3 w-3" />
                    CHANGE
                  </button>
                </div>
                <SchematicUpload
                  productId={selectedProduct.id}
                  onSuccess={() => setContributeOpen(false)}
                />
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-400 mb-4">
                  Search for the product this document belongs to, then upload the file.
                </p>
                <div className="relative mb-4">
                  <input
                    type="text"
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    placeholder="Search for a product (e.g. Cisco RV340, iPhone 12)..."
                    className="input-cyber pl-10"
                    autoFocus
                  />
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                </div>
                {productSearch.length >= 2 && productSearchResults && (
                  <div className="space-y-1">
                    {productSearchResults.results.length === 0 ? (
                      <p className="text-sm text-gray-500 py-4 text-center font-mono">No products found. <Link to="/submit" className="text-cyber-cyan hover:underline">Submit it first?</Link></p>
                    ) : (
                      productSearchResults.results.map((product: any) => (
                        <button
                          key={product.id}
                          onClick={() => setSelectedProduct({ id: product.id, label: `${product.manufacturer} ${product.model_number}` })}
                          className="w-full text-left p-3 border border-cyber-light/20 hover:border-cyber-green/50 hover:bg-cyber-green/5 transition-all flex items-center gap-3"
                        >
                          <Cpu className="h-4 w-4 text-gray-500 flex-shrink-0" />
                          <div>
                            <div className="text-white font-mono text-sm">{product.manufacturer} {product.model_number}</div>
                            {product.category_display && (
                              <div className="text-xs text-gray-500">{product.category_display}</div>
                            )}
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                )}
                {productSearch.length < 2 && (
                  <p className="text-xs text-gray-600 font-mono text-center py-2">Type at least 2 characters to search</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Filters Bar */}
        <div className="card-cyber p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <input
                type="text"
                value={search}
                onChange={(e) => updateFilter('search', e.target.value)}
                placeholder="Search by title, product, description..."
                className="input-cyber pl-10"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
            </div>

            {/* Schematic Type */}
            <div className="relative">
              <select
                value={schematicType}
                onChange={(e) => updateFilter('schematic_type', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full lg:w-48"
              >
                {SCHEMATIC_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500 pointer-events-none" />
            </div>

            {/* Source Type */}
            <div className="relative">
              <select
                value={sourceType}
                onChange={(e) => updateFilter('source_type', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full lg:w-44"
              >
                {SOURCE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
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
                className="input-cyber appearance-none pr-10 w-full lg:w-44"
              >
                <option value="-download_count">Most Downloaded</option>
                <option value="-uploaded_at">Newest First</option>
                <option value="uploaded_at">Oldest First</option>
                <option value="title">Title A-Z</option>
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
                    ? 'border-cyber-green text-cyber-green bg-cyber-green/10'
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
                    ? 'border-cyber-green text-cyber-green bg-cyber-green/10'
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
            {data.count} documents found
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card-cyber p-4">
                <Skeleton variant="rectangular" className="aspect-[4/3] mb-4" />
                <Skeleton width="30%" className="mb-2" />
                <Skeleton width="80%" height={20} className="mb-2" />
                <div className="flex gap-4 mt-3">
                  <Skeleton width={50} />
                  <Skeleton width={30} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Schematics Grid/List */}
        {data && !isLoading && (
          <div
            className={clsx(
              viewMode === 'grid'
                ? 'grid sm:grid-cols-2 lg:grid-cols-3 gap-6'
                : 'flex flex-col gap-4'
            )}
          >
            {data.results.map((schematic) => (
              <div
                key={schematic.id}
                className={clsx(
                  'card-cyber hover:border-cyber-green/50 transition-all group',
                  viewMode === 'grid' ? 'p-4' : 'p-4 flex gap-4'
                )}
              >
                {/* File Icon */}
                <div
                  className={clsx(
                    'bg-cyber-black flex items-center justify-center border border-cyber-light/20',
                    viewMode === 'grid' ? 'aspect-[4/3] mb-4' : 'w-20 h-20 flex-shrink-0'
                  )}
                >
                  <div className="text-center">
                    <span className="text-3xl">{getFileTypeIcon(schematic.file_type)}</span>
                    <div className="text-xs font-mono text-gray-500 mt-1 uppercase">
                      {schematic.file_type}
                    </div>
                  </div>
                </div>

                {/* Info */}
                <div className={viewMode === 'list' ? 'flex-1 min-w-0' : ''}>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="badge-cyber text-cyber-green border-cyber-green text-[10px]">
                      {schematic.schematic_type_display || schematic.schematic_type}
                    </span>
                    {schematic.is_approved && (
                      <span title="Approved">
                        <CheckCircle className="h-3.5 w-3.5 text-cyber-green" />
                      </span>
                    )}
                    {schematic.source_type && (
                      <span className="text-[10px] font-mono text-gray-500">
                        {schematic.source_type_display || schematic.source_type}
                      </span>
                    )}
                  </div>

                  <h3 className="font-semibold text-white group-hover:text-cyber-green transition-colors line-clamp-2 mb-1">
                    {schematic.title}
                  </h3>

                  {schematic.version && (
                    <div className="text-xs text-gray-500 font-mono mb-2">
                      Version: {schematic.version}
                    </div>
                  )}

                  {schematic.description && viewMode === 'list' && (
                    <p className="text-sm text-gray-400 line-clamp-2 mb-2">
                      {schematic.description}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                    <span>{formatFileSize(schematic.file_size)}</span>
                    <span className="flex items-center gap-1">
                      <Download className="h-3 w-3" />
                      {schematic.download_count}
                    </span>
                    {schematic.uploaded_by && (
                      <span>by {schematic.uploaded_by.username}</span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="mt-3 pt-3 border-t border-cyber-light/20 flex items-center gap-3">
                    {schematic.file_url && (
                      <a
                        href={schematic.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-mono text-cyber-green hover:text-white transition-colors flex items-center gap-1"
                      >
                        <Download className="h-3.5 w-3.5" />
                        DOWNLOAD
                      </a>
                    )}
                    {schematic.source_url && (
                      <a
                        href={schematic.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-mono text-gray-500 hover:text-cyber-cyan transition-colors flex items-center gap-1"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        SOURCE
                      </a>
                    )}
                    <Link
                      to={`/products/${schematic.product}`}
                      className="text-xs font-mono text-gray-500 hover:text-cyber-cyan transition-colors flex items-center gap-1"
                    >
                      <Cpu className="h-3.5 w-3.5" />
                      PRODUCT
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {data && data.results.length === 0 && (
          <div className="text-center py-20">
            <FileText className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="font-display text-xl text-white mb-2">NO DOCUMENTS FOUND</h3>
            <p className="text-gray-500 mb-6">
              Try adjusting your search or filters
            </p>
            <Link to="/submit" className="btn-cyber btn-cyber-green">
              UPLOAD A SCHEMATIC
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

        {/* Info box */}
        <div className="mt-12 p-4 border border-cyber-light/20 bg-cyber-dark/50">
          <h3 className="font-mono text-sm text-cyber-green mb-2">// ABOUT SCHEMATICS</h3>
          <p className="text-xs text-gray-500 leading-relaxed">
            This archive contains service manuals, schematics, and technical documentation
            contributed by the repair community. All documents are provided for educational
            and repair purposes in support of the Right to Repair movement. If you have
            documentation to share, please{' '}
            <button onClick={() => { setContributeOpen(true); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="text-cyber-green hover:underline">contribute</button>.
          </p>
        </div>
      </div>
    </div>
  );
}
