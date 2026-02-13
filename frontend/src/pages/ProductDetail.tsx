import { useParams, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import ImageUpload from '../components/ImageUpload';
import SchematicUpload from '../components/SchematicUpload';
import AddComponentForm from '../components/AddComponentForm';
import BomImport from '../components/BomImport';
import BatchAddComponents from '../components/BatchAddComponents';
import ReportModal from '../components/ReportModal';
import ProductComments from '../components/ProductComments';
import {
  Cpu,
  FileText,
  Download,
  ExternalLink,
  Image,
  ChevronRight,
  Upload,
  Camera,
  Flag,
  Share2,
  MessageSquare,
} from 'lucide-react';
import clsx from 'clsx';
import { useState } from 'react';
import LazyImage from '../components/LazyImage';

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'images' | 'components' | 'schematics' | 'comments'>('overview');
  const [selectedImage, setSelectedImage] = useState(0);
  const [showAddComponent, setShowAddComponent] = useState(false);
  const [showBomImport, setShowBomImport] = useState(false);
  const [showBatchAdd, setShowBatchAdd] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);

  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: () => products.get(id!),
    enabled: !!id,
  });

  const { data: componentList } = useQuery({
    queryKey: ['product', id, 'components'],
    queryFn: () => products.components(id!),
    enabled: !!id && activeTab === 'components',
  });

  const { data: schematicList } = useQuery({
    queryKey: ['product', id, 'schematics'],
    queryFn: () => products.schematics(id!),
    enabled: !!id && activeTab === 'schematics',
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-cyber-cyan font-mono animate-pulse">
          LOADING PRODUCT DATA...
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="py-20 text-center">
        <h2 className="font-display text-2xl text-white mb-4">PRODUCT NOT FOUND</h2>
        <Link to="/products" className="btn-cyber">
          BACK TO DATABASE
        </Link>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-7xl px-4">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm font-mono text-gray-500 mb-6">
          <Link to="/products" className="hover:text-cyber-cyan">
            Products
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-gray-400">{product.manufacturer}</span>
          <ChevronRight className="h-4 w-4" />
          <span className="text-white">{product.model_number}</span>
        </nav>

        <div className="grid lg:grid-cols-2 gap-8 mb-8">
          {/* Image Gallery */}
          <div>
            <div className="card-cyber p-4 mb-4">
              <div className="aspect-video bg-cyber-black flex items-center justify-center">
                {product.images && product.images[selectedImage] ? (
                  <img
                    src={product.images[selectedImage].image}
                    alt={product.model_number}
                    className="max-w-full max-h-full object-contain"
                  />
                ) : (
                  <div className="text-center text-gray-600">
                    <Image className="h-16 w-16 mx-auto mb-2" />
                    <p className="font-mono text-sm">NO IMAGES</p>
                  </div>
                )}
              </div>
            </div>

            {/* Thumbnails and Add button */}
            <div className="flex gap-2 overflow-x-auto scrollbar-hide">
              {product.images && product.images.map((img, idx) => (
                <button
                  key={img.id}
                  onClick={() => setSelectedImage(idx)}
                  className={clsx(
                    'w-20 h-20 flex-shrink-0 border',
                    idx === selectedImage
                      ? 'border-cyber-cyan'
                      : 'border-cyber-light/30 hover:border-cyber-light'
                  )}
                >
                  <LazyImage
                    src={img.thumbnail || img.image}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
              {isAuthenticated && (
                <button
                  onClick={() => setActiveTab('images')}
                  className="w-20 h-20 flex-shrink-0 border border-dashed border-cyber-cyan/50 hover:border-cyber-cyan hover:bg-cyber-cyan/10 transition-all flex flex-col items-center justify-center text-cyber-cyan"
                >
                  <Upload className="h-5 w-5 mb-1" />
                  <span className="text-[10px] font-mono">ADD</span>
                </button>
              )}
            </div>
          </div>

          {/* Product Info */}
          <div>
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-cyber-cyan font-mono text-sm mb-1">
                  {product.manufacturer}
                </div>
                <h1 className="font-display text-3xl font-bold text-white">
                  {product.model_number}
                </h1>
                {product.revision && (
                  <div className="text-gray-500 font-mono text-sm mt-1">
                    Revision: {product.revision}
                  </div>
                )}
              </div>
              {product.is_featured && (
                <span className="badge-cyber text-cyber-yellow border-cyber-yellow">
                  FEATURED
                </span>
              )}
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-6">
              <div className="card-cyber p-2 sm:p-4 text-center">
                <div className="text-xl sm:text-2xl font-display font-bold text-cyber-cyan">
                  {product.component_count}
                </div>
                <div className="text-[10px] sm:text-xs font-mono text-gray-500">COMPONENTS</div>
              </div>
              <div className="card-cyber p-2 sm:p-4 text-center">
                <div className="text-xl sm:text-2xl font-display font-bold text-cyber-pink">
                  {product.image_count}
                </div>
                <div className="text-[10px] sm:text-xs font-mono text-gray-500">IMAGES</div>
              </div>
              <div className="card-cyber p-2 sm:p-4 text-center">
                <div className="text-xl sm:text-2xl font-display font-bold text-cyber-green">
                  {product.schematic_count}
                </div>
                <div className="text-[10px] sm:text-xs font-mono text-gray-500">SCHEMATICS</div>
              </div>
            </div>

            {/* Details */}
            <div className="card-cyber p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Category</span>
                  <p className="text-white font-mono">
                    {product.category_display || product.category}
                  </p>
                </div>
                {product.region && (
                  <div>
                    <span className="text-gray-500">Region</span>
                    <p className="text-white font-mono">{product.region}</p>
                  </div>
                )}
                {product.year_manufactured && (
                  <div>
                    <span className="text-gray-500">Year</span>
                    <p className="text-white font-mono">{product.year_manufactured}</p>
                  </div>
                )}
                {product.fcc_id && (
                  <div>
                    <span className="text-gray-500">FCC ID</span>
                    <p className="text-cyber-cyan font-mono">
                      <a
                        href={`https://fccid.io/${product.fcc_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline inline-flex items-center gap-1"
                      >
                        {product.fcc_id}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </p>
                  </div>
                )}
                {product.ic_id && (
                  <div>
                    <span className="text-gray-500">IC ID</span>
                    <p className="text-white font-mono">{product.ic_id}</p>
                  </div>
                )}
                {product.part_number && (
                  <div>
                    <span className="text-gray-500">Part Number</span>
                    <p className="text-white font-mono">{product.part_number}</p>
                  </div>
                )}
              </div>

              {product.description && (
                <div className="border-t border-cyber-light/30 pt-4">
                  <span className="text-gray-500 text-sm">Description</span>
                  <p className="text-gray-300 mt-1">{product.description}</p>
                </div>
              )}

              {/* Actions */}
              <div className="border-t border-cyber-light/30 pt-4 mt-4 flex flex-wrap items-center gap-3 sm:gap-4">
                <button
                  onClick={() => {
                    // Export product data as JSON
                    products.exportData(id!).then((data) => {
                      const blob = new Blob([JSON.stringify(data, null, 2)], {
                        type: 'application/json',
                      });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${product?.manufacturer}-${product?.model_number}.json`.replace(/\s+/g, '-').toLowerCase();
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                    });
                  }}
                  className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-cyan transition-colors"
                >
                  <Share2 className="h-3 w-3" />
                  Export JSON
                </button>
                <button
                  onClick={() => {
                    // Export BOM as CSV
                    products.exportCsv(id!).then((csv) => {
                      const blob = new Blob([csv], { type: 'text/csv' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${product?.manufacturer}-${product?.model_number}-bom.csv`.replace(/\s+/g, '-').toLowerCase();
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                    });
                  }}
                  className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-green transition-colors"
                >
                  <Download className="h-3 w-3" />
                  Export BOM
                </button>
                {isAuthenticated && (
                  <button
                    onClick={() => setShowReportModal(true)}
                    className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-yellow transition-colors"
                  >
                    <Flag className="h-3 w-3" />
                    Report an issue
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-cyber-light/30 mb-6 -mx-4 sm:mx-0">
          <div className="flex gap-1 sm:gap-6 overflow-x-auto scrollbar-hide px-4 sm:px-0">
            {[
              { key: 'overview', label: 'Overview', icon: Cpu },
              { key: 'images', label: 'Images', icon: Camera },
              { key: 'components', label: 'Parts', icon: Cpu },
              { key: 'schematics', label: 'Docs', icon: FileText },
              { key: 'comments', label: 'Comments', icon: MessageSquare, count: product.comment_count },
            ].map(({ key, label, icon: Icon, count }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as typeof activeTab)}
                className={clsx(
                  'flex items-center gap-1.5 sm:gap-2 py-3 sm:py-4 px-2 sm:px-0 border-b-2 font-mono text-xs sm:text-sm transition-colors whitespace-nowrap',
                  activeTab === key
                    ? 'border-cyber-cyan text-cyber-cyan'
                    : 'border-transparent text-gray-500 hover:text-white'
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
                {count !== undefined && count > 0 && (
                  <span className="text-[10px] bg-cyber-cyan/20 text-cyber-cyan px-1.5 py-0.5 rounded-full font-mono">
                    {count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="card-cyber p-6">
            {product.teardown_notes ? (
              <div>
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  TEARDOWN NOTES
                </h3>
                <div className="prose prose-invert max-w-none text-gray-300">
                  {product.teardown_notes}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Cpu className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No teardown notes available yet.</p>
                <Link to="/submit" className="text-cyber-cyan hover:underline text-sm mt-2 inline-block">
                  Contribute notes
                </Link>
              </div>
            )}
          </div>
        )}

        {activeTab === 'images' && (
          <div className="space-y-6">
            {/* Existing Images Grid */}
            {product.images && product.images.length > 0 && (
              <div>
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  PRODUCT IMAGES ({product.images.length})
                </h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {product.images.map((img, idx) => (
                    <div
                      key={img.id}
                      className="card-cyber p-2 cursor-pointer hover:border-cyber-cyan/50 transition-all"
                      onClick={() => {
                        setSelectedImage(idx);
                        setActiveTab('overview');
                      }}
                    >
                      <div className="aspect-video bg-cyber-black mb-2">
                        <LazyImage
                          src={img.thumbnail || img.image}
                          alt={img.caption || `Image ${idx + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="badge-cyber text-gray-400 border-gray-600">
                          {img.image_type}
                        </span>
                        {img.caption && (
                          <span className="text-gray-500 truncate ml-2">
                            {img.caption}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload Section */}
            {isAuthenticated ? (
              <div className="card-cyber p-6">
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  <Upload className="h-5 w-5 inline mr-2 text-cyber-cyan" />
                  UPLOAD IMAGES
                </h3>
                <ImageUpload
                  productId={id!}
                  onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ['product', id] });
                  }}
                />
              </div>
            ) : (
              <div className="card-cyber p-8 text-center">
                <Camera className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 mb-4">
                  Log in to upload images for this product.
                </p>
                <Link to="/login" className="btn-cyber">
                  LOGIN TO CONTRIBUTE
                </Link>
              </div>
            )}

            {/* Guidelines */}
            <div className="p-4 border border-cyber-light/20 bg-cyber-dark/50">
              <h4 className="font-mono text-sm text-cyber-cyan mb-2">// IMAGE GUIDELINES</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• High resolution photos preferred (min 1024px width)</li>
                <li>• Include PCB front/back, labels, and internal components</li>
                <li>• Well-lit photos with minimal blur</li>
                <li>• Add descriptive captions to help others</li>
                <li>• Max file size: 10MB per image</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'components' && (
          <div className="space-y-6">
            {/* Components Table */}
            {componentList && componentList.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-display text-lg font-semibold text-white">
                    DOCUMENTED COMPONENTS ({componentList.length})
                  </h3>
                  {isAuthenticated && !showAddComponent && !showBomImport && !showBatchAdd && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowBomImport(true)}
                        className="btn-cyber btn-cyber-green text-sm py-1.5"
                      >
                        IMPORT BOM
                      </button>
                      <button
                        onClick={() => setShowBatchAdd(true)}
                        className="btn-cyber text-sm py-1.5"
                      >
                        BATCH ADD
                      </button>
                      <button
                        onClick={() => setShowAddComponent(true)}
                        className="btn-cyber text-sm py-1.5"
                      >
                        + ADD
                      </button>
                    </div>
                  )}
                </div>
                {/* Desktop table view */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-cyber-light/30 text-left">
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">DESIGNATOR</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">PART NUMBER</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">VALUE</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">MANUFACTURER</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">TYPE</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">QTY</th>
                      </tr>
                    </thead>
                    <tbody>
                      {componentList.map((pc: any) => (
                        <tr
                          key={pc.id}
                          className="border-b border-cyber-light/20 hover:bg-cyber-light/10"
                        >
                          <td className="py-3 px-4 font-mono text-cyber-cyan">
                            {pc.reference_designator || '-'}
                          </td>
                          <td className="py-3 px-4">
                            <Link
                              to={`/components/${pc.component.id}/products`}
                              className="text-white hover:text-cyber-pink"
                            >
                              {pc.component.part_number}
                            </Link>
                          </td>
                          <td className="py-3 px-4 font-mono text-cyber-yellow text-sm">
                            {pc.component.primary_value || '-'}
                          </td>
                          <td className="py-3 px-4 text-gray-400">
                            {pc.component.manufacturer}
                          </td>
                          <td className="py-3 px-4">
                            <span className="badge-cyber text-cyber-pink border-cyber-pink/50 text-[10px]">
                              {pc.component.component_type_display || pc.component.component_type}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-gray-400">{pc.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Mobile card view */}
                <div className="md:hidden space-y-3">
                  {componentList.map((pc: any) => (
                    <Link
                      key={pc.id}
                      to={`/components/${pc.component.id}/products`}
                      className="card-cyber p-3 block hover:border-cyber-pink/50 transition-all"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-white truncate">
                            {pc.component.part_number}
                          </div>
                          <div className="text-xs text-gray-400 truncate">
                            {pc.component.manufacturer}
                            {pc.component.primary_value && (
                              <span className="ml-2 text-cyber-yellow">{pc.component.primary_value}</span>
                            )}
                          </div>
                        </div>
                        {pc.reference_designator && (
                          <span className="font-mono text-cyber-cyan text-sm flex-shrink-0">
                            {pc.reference_designator}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="badge-cyber text-cyber-pink border-cyber-pink/50 text-[10px]">
                          {pc.component.component_type_display || pc.component.component_type}
                        </span>
                        {pc.quantity > 1 && (
                          <span className="text-xs text-gray-500">×{pc.quantity}</span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Add Component Form */}
            {isAuthenticated && showAddComponent && (
              <div className="card-cyber p-6">
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  <Cpu className="h-5 w-5 inline mr-2 text-cyber-pink" />
                  ADD COMPONENT
                </h3>
                <AddComponentForm
                  productId={id!}
                  onSuccess={() => {
                    setShowAddComponent(false);
                    queryClient.invalidateQueries({ queryKey: ['product', id, 'components'] });
                  }}
                  onCancel={() => setShowAddComponent(false)}
                />
              </div>
            )}

            {/* BOM Import */}
            {isAuthenticated && showBomImport && (
              <div className="card-cyber p-6">
                <BomImport
                  productId={id!}
                  onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ['product', id, 'components'] });
                    queryClient.invalidateQueries({ queryKey: ['product', id] });
                  }}
                  onClose={() => setShowBomImport(false)}
                />
              </div>
            )}

            {/* Batch Add Components */}
            {isAuthenticated && showBatchAdd && (
              <div className="card-cyber p-6">
                <BatchAddComponents
                  productId={id!}
                  onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ['product', id, 'components'] });
                    queryClient.invalidateQueries({ queryKey: ['product', id] });
                  }}
                  onClose={() => setShowBatchAdd(false)}
                />
              </div>
            )}

            {/* Empty state / Add button for no components */}
            {(!componentList || componentList.length === 0) && !showAddComponent && !showBomImport && !showBatchAdd && (
              <div className="card-cyber p-8 text-center">
                <Cpu className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 mb-4">No components documented yet.</p>
                {isAuthenticated ? (
                  <div className="flex items-center justify-center gap-3">
                    <button
                      onClick={() => setShowBomImport(true)}
                      className="btn-cyber btn-cyber-green"
                    >
                      IMPORT BOM
                    </button>
                    <button
                      onClick={() => setShowBatchAdd(true)}
                      className="btn-cyber"
                    >
                      BATCH ADD
                    </button>
                    <button
                      onClick={() => setShowAddComponent(true)}
                      className="btn-cyber"
                    >
                      ADD COMPONENT
                    </button>
                  </div>
                ) : (
                  <Link to="/login" className="btn-cyber">
                    LOGIN TO ADD COMPONENTS
                  </Link>
                )}
              </div>
            )}

            {/* Add button when logged in but no form shown and has components */}
            {isAuthenticated && !showAddComponent && componentList && componentList.length === 0 && (
              <div />
            )}

            {/* Guidelines */}
            <div className="p-4 border border-cyber-light/20 bg-cyber-dark/50">
              <h4 className="font-mono text-sm text-cyber-pink mb-2">// COMPONENT GUIDELINES</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• Include reference designators (U1, R5, C12) when visible</li>
                <li>• Search for existing components before adding new ones</li>
                <li>• Add datasheet links when available</li>
                <li>• Document major ICs, regulators, and interesting components</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'schematics' && (
          <div className="space-y-6">
            {/* Existing Schematics */}
            {schematicList && schematicList.length > 0 && (
              <div>
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  AVAILABLE SCHEMATICS ({schematicList.length})
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {schematicList.map((schematic) => (
                    <div key={schematic.id} className="card-cyber p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="badge-cyber text-cyber-green border-cyber-green text-[10px] mb-2">
                            {schematic.schematic_type_display || schematic.schematic_type}
                          </span>
                          <h4 className="font-semibold text-white">{schematic.title}</h4>
                          {schematic.description && (
                            <p className="text-sm text-gray-400 mt-1">{schematic.description}</p>
                          )}
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <span>{schematic.file_type?.toUpperCase()}</span>
                            {schematic.file_size && (
                              <span>{(schematic.file_size / 1024 / 1024).toFixed(1)} MB</span>
                            )}
                            <span>{schematic.download_count} downloads</span>
                          </div>
                        </div>
                        <a
                          href={schematic.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-cyber btn-cyber-green py-2 px-3"
                        >
                          <Download className="h-4 w-4" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload Section */}
            {isAuthenticated ? (
              <div className="card-cyber p-6">
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  <Upload className="h-5 w-5 inline mr-2 text-cyber-green" />
                  UPLOAD SCHEMATIC
                </h3>
                <SchematicUpload
                  productId={id!}
                  onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ['product', id, 'schematics'] });
                  }}
                />
              </div>
            ) : (
              <div className="card-cyber p-8 text-center">
                <FileText className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 mb-4">
                  Log in to upload schematics for this product.
                </p>
                <Link to="/login" className="btn-cyber">
                  LOGIN TO CONTRIBUTE
                </Link>
              </div>
            )}

            {/* Empty state for no schematics */}
            {(!schematicList || schematicList.length === 0) && !isAuthenticated && (
              <div className="card-cyber p-8 text-center text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No schematics available yet.</p>
              </div>
            )}

            {/* Guidelines */}
            <div className="p-4 border border-cyber-light/20 bg-cyber-dark/50">
              <h4 className="font-mono text-sm text-cyber-green mb-2">// SCHEMATIC GUIDELINES</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• PDFs preferred for multi-page schematics</li>
                <li>• Include version/revision info when known</li>
                <li>• Provide source attribution when possible</li>
                <li>• Max file size: 50MB per schematic</li>
                <li>• Supported formats: PDF, PNG, JPG, ZIP</li>
              </ul>
            </div>
          </div>
        )}
        {activeTab === 'comments' && (
          <ProductComments productId={id!} />
        )}
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        contentType="products.product"
        objectId={id!}
        itemName={`${product?.manufacturer} ${product?.model_number}`}
      />
    </div>
  );
}
