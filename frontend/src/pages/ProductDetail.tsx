import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { products, schematics, firmware, junkbin } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import ImageUpload from '../components/ImageUpload';
import SchematicUpload from '../components/SchematicUpload';
import FirmwareUpload from '../components/FirmwareUpload';
import AddComponentForm from '../components/AddComponentForm';
import BomImport from '../components/BomImport';
import BomPdfExtract from '../components/BomPdfExtract';
import BatchAddComponents from '../components/BatchAddComponents';
import ReportModal from '../components/ReportModal';
import AddToJunkbinModal from '../components/AddToJunkbinModal';
import EditProductModal from '../components/EditProductModal';
import ProductComments from '../components/ProductComments';
import ComponentVoteButtons from '../components/ComponentVoteButtons';
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
  Archive,
  Pencil,
  Trash2,
  ArrowLeftRight,
  HardDrive,
  Sparkles,
  ScanText,
} from 'lucide-react';
import type { JunkbinItem, Schematic } from '../types';
import clsx from 'clsx';
import { useState } from 'react';
import LazyImage from '../components/LazyImage';
import Lightbox from '../components/Lightbox';
import RetroactiveBgRemoval from '../components/RetroactiveBgRemoval';

// Schematic types that plausibly contain a real parts list/table - circuit
// diagrams don't, and need the separate OCR + spatial-matching pipeline.
const BOM_EXTRACTABLE_SCHEMATIC_TYPES = ['service_manual', 'bom'];
// Circuit-diagram-shaped types where OCR-scanning for designator labels is
// the relevant technique instead (components are drawn symbols, not table rows).
const OCR_EXTRACTABLE_SCHEMATIC_TYPES = ['full_schematic', 'block_diagram', 'pcb_layout', 'wiring_diagram', 'pinout'];

function SwapItemCard({ item, currentUserId, isAuthenticated, t }: {
  item: JunkbinItem;
  currentUserId?: string;
  isAuthenticated: boolean;
  t: (key: string, options?: Record<string, unknown>) => string;
}) {
  const canContact =
    isAuthenticated && currentUserId !== item.user.id && item.item_type === 'have' && item.status === 'available';
  const conditionLabels: Record<string, string> = {
    new: t('common.condition.new'),
    working: t('common.condition.working'),
    broken: t('common.condition.broken'),
    unknown: t('common.condition.unknown'),
  };
  return (
    <div className="card-cyber p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        {item.item_type === 'have' && (
          <span className={item.status === 'available'
            ? 'badge-cyber text-[10px] text-cyber-green border-cyber-green'
            : 'badge-cyber text-[10px] text-gray-500 border-gray-600'
          }>
            {item.status === 'available' ? t('product_detail.available') : t('product_detail.not_for_trade')}
          </span>
        )}
        {item.item_type === 'have' && (
          <span className="badge-cyber text-[10px] text-gray-400 border-gray-600">
            {conditionLabels[item.condition] || item.condition}
          </span>
        )}
        {item.quantity > 1 && (
          <span className="text-xs text-gray-500 font-mono ml-auto">×{item.quantity}</span>
        )}
      </div>
      {item.notes && (
        <p className="text-sm text-gray-400 line-clamp-2">{item.notes}</p>
      )}
      <div className="flex items-center justify-between pt-2 border-t border-cyber-light/20 mt-auto">
        <Link
          to={`/users/${item.user.id}`}
          className="flex items-center gap-2 group min-w-0"
        >
          <div className="w-6 h-6 rounded-full bg-cyber-gray border border-cyber-light/30 flex items-center justify-center overflow-hidden flex-shrink-0">
            {item.user.avatar ? (
              <img src={item.user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              <span className="text-gray-500 font-mono text-[10px]">
                {item.user.username.charAt(0).toUpperCase()}
              </span>
            )}
          </div>
          <span className="text-xs text-gray-400 group-hover:text-cyber-cyan transition-colors font-mono truncate">
            {item.user.display_name || item.user.username}
          </span>
        </Link>
        {canContact && (
          <Link
            to={`/messages/new?user=${item.user.id}`}
            className="flex items-center gap-1 text-xs text-cyber-cyan hover:text-white transition-colors font-mono flex-shrink-0 ml-2"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            {t('product_detail.contact')}
          </Link>
        )}
      </div>
    </div>
  );
}

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, user } = useAuth();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'images' | 'components' | 'schematics' | 'firmware' | 'comments' | 'swap'>('overview');
  const [selectedImage, setSelectedImage] = useState(0);
  const [showAddComponent, setShowAddComponent] = useState(false);
  const [showBomImport, setShowBomImport] = useState(false);
  const [showBomPdfExtract, setShowBomPdfExtract] = useState(false);
  const [extractingSchematic, setExtractingSchematic] = useState<Schematic | null>(null);
  const [extractingMode, setExtractingMode] = useState<'text' | 'ocr'>('text');
  const [showBatchAdd, setShowBatchAdd] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showJunkbinModal, setShowJunkbinModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

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

  const { data: firmwareList } = useQuery({
    queryKey: ['product', id, 'firmware'],
    queryFn: () => products.firmware(id!),
    enabled: !!id && activeTab === 'firmware',
  });

  const { data: swapCount } = useQuery({
    queryKey: ['junkbin', 'product', id, 'count'],
    queryFn: () => junkbin.list({ content_type: 'product', object_id: id }),
    enabled: !!id,
  });

  const { data: swapHave } = useQuery({
    queryKey: ['junkbin', 'product', id, 'have'],
    queryFn: () => junkbin.list({ content_type: 'product', object_id: id, item_type: 'have' }),
    enabled: !!id && activeTab === 'swap',
  });

  const { data: swapWant } = useQuery({
    queryKey: ['junkbin', 'product', id, 'want'],
    queryFn: () => junkbin.list({ content_type: 'product', object_id: id, item_type: 'want' }),
    enabled: !!id && activeTab === 'swap',
  });

  const deleteMutation = useMutation({
    mutationFn: () => products.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      navigate('/products');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-cyber-cyan font-mono animate-pulse">
          {t('product_detail.loading_data')}
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="py-20 text-center">
        <h2 className="font-display text-2xl text-white mb-4">{t('product_detail.not_found_title')}</h2>
        <Link to="/products" className="btn-cyber">
          {t('product_detail.back_db')}
        </Link>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-screen-2xl px-4">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm font-mono text-gray-500 mb-6">
          <Link to="/products" className="hover:text-cyber-cyan">
            {t('product_detail.breadcrumb_products')}
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
              <div className="aspect-[4/3] bg-cyber-black flex items-center justify-center">
                {product.images && product.images[selectedImage] ? (
                  <img
                    src={product.images[selectedImage].image}
                    alt={product.model_number}
                    className="max-w-full max-h-full object-contain bg-cyber-black cursor-zoom-in"
                    onClick={() => setLightboxIndex(selectedImage)}
                    title="Click to enlarge"
                  />
                ) : (
                  <div className="text-center text-gray-600">
                    <Image className="h-16 w-16 mx-auto mb-2" />
                    <p className="font-mono text-sm">{t('product_detail.no_images')}</p>
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
                    'w-24 aspect-[4/3] flex-shrink-0 border',
                    idx === selectedImage
                      ? 'border-cyber-cyan'
                      : 'border-cyber-light/30 hover:border-cyber-light'
                  )}
                >
                  <LazyImage
                    src={img.thumbnail || img.image}
                    alt=""
                    className="w-full h-full object-cover bg-cyber-black"
                  />
                </button>
              ))}
              {isAuthenticated && (
                <button
                  onClick={() => setActiveTab('images')}
                  className="w-24 aspect-[4/3] flex-shrink-0 border border-dashed border-cyber-cyan/50 hover:border-cyber-cyan hover:bg-cyber-cyan/10 transition-all flex flex-col items-center justify-center text-cyber-cyan"
                >
                  <Upload className="h-5 w-5 mb-1" />
                  <span className="text-[10px] font-mono">{t('product_detail.add_image_btn')}</span>
                </button>
              )}
            </div>

            {/* PCBTracer button */}
            {product.images && product.images.length > 0 && (
              <div className="mt-3">
                <a
                  href={`https://pcbtracer.com?image=${encodeURIComponent(product.images[selectedImage]?.image || product.images[0].image)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-green transition-colors font-mono"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  {t('product_detail.open_in_pcbtracer')}
                </a>
              </div>
            )}
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
                    {t('product_detail.revision')} {product.revision}
                  </div>
                )}
              </div>
              {product.is_featured && (
                <span className="badge-cyber text-cyber-yellow border-cyber-yellow">
                  {t('product_detail.featured')}
                </span>
              )}
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mb-6">
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
              <div className="card-cyber p-2 sm:p-4 text-center">
                <div className="text-xl sm:text-2xl font-display font-bold text-purple-400">
                  {product.firmware_count}
                </div>
                <div className="text-[10px] sm:text-xs font-mono text-gray-500">FIRMWARE</div>
              </div>
            </div>

            {/* Details */}
            <div className="card-cyber p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">{t('product_detail.label_category')}</span>
                  <p className="text-white font-mono">
                    {product.category_display || product.category}
                  </p>
                </div>
                {product.region && (
                  <div>
                    <span className="text-gray-500">{t('product_detail.label_region')}</span>
                    <p className="text-white font-mono">{product.region}</p>
                  </div>
                )}
                {product.year_manufactured && (
                  <div>
                    <span className="text-gray-500">{t('product_detail.label_year')}</span>
                    <p className="text-white font-mono">{product.year_manufactured}</p>
                  </div>
                )}
                {product.fcc_id && (
                  <div>
                    <span className="text-gray-500">{t('product_detail.label_fcc_id')}</span>
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
                    <span className="text-gray-500">{t('product_detail.label_ic_id')}</span>
                    <p className="text-white font-mono">{product.ic_id}</p>
                  </div>
                )}
                {product.part_number && (
                  <div>
                    <span className="text-gray-500">{t('product_detail.label_part_number')}</span>
                    <p className="text-white font-mono">{product.part_number}</p>
                  </div>
                )}
              </div>

              {product.description && (
                <div className="border-t border-cyber-light/30 pt-4">
                  <span className="text-gray-500 text-sm">{t('product_detail.label_description')}</span>
                  <p className="text-gray-300 mt-1">{product.description}</p>
                </div>
              )}

              {/* Actions */}
              <div className="border-t border-cyber-light/30 pt-4 mt-4 flex flex-wrap items-center gap-3 sm:gap-4">
                {isAuthenticated && (user?.is_staff || product.created_by?.id === user?.id) && (
                  <button
                    onClick={() => setShowEditModal(true)}
                    className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-cyan transition-colors"
                  >
                    <Pencil className="h-3 w-3" />
                    {t('product_detail.edit')}
                  </button>
                )}
                {isAuthenticated && (user?.is_staff || product.created_by?.id === user?.id) && (
                  !confirmDelete ? (
                    <button
                      onClick={() => setConfirmDelete(true)}
                      className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-pink transition-colors"
                    >
                      <Trash2 className="h-3 w-3" />
                      Delete
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-2 text-xs">
                      <span className="text-cyber-pink">{t('product_detail.are_you_sure')}</span>
                      <button
                        onClick={() => deleteMutation.mutate()}
                        disabled={deleteMutation.isPending}
                        className="text-cyber-pink hover:text-white font-mono text-xs border border-cyber-pink/50 px-2 py-0.5"
                      >
                        {deleteMutation.isPending ? t('product_detail.deleting') : t('product_detail.confirm_yes')}
                      </button>
                      <button
                        onClick={() => setConfirmDelete(false)}
                        className="text-gray-500 hover:text-white font-mono text-xs"
                      >
                        {t('common.cancel')}
                      </button>
                    </span>
                  )
                )}
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
                  {t('product_detail.share')}
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
                  {t('product_detail.export_bom')}
                </button>
                {isAuthenticated && (
                  <button
                    onClick={() => setShowJunkbinModal(true)}
                    className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-cyan transition-colors"
                  >
                    <Archive className="h-3 w-3" />
                    {t('product_detail.add_to_junkbin')}
                  </button>
                )}
                {isAuthenticated && (
                  <button
                    onClick={() => setShowReportModal(true)}
                    className="flex items-center gap-2 text-xs text-gray-500 hover:text-cyber-yellow transition-colors"
                  >
                    <Flag className="h-3 w-3" />
                    {t('product_detail.report')}
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
              { key: 'overview', label: t('product_detail.tab_overview'), icon: Cpu },
              { key: 'images', label: t('product_detail.tab_images'), icon: Camera },
              { key: 'components', label: t('product_detail.tab_parts'), icon: Cpu },
              { key: 'schematics', label: t('product_detail.tab_docs'), icon: FileText },
              { key: 'firmware', label: t('product_detail.tab_firmware'), icon: HardDrive },
              { key: 'comments', label: t('product_detail.tab_comments'), icon: MessageSquare, count: product.comment_count },
              { key: 'swap', label: t('product_detail.tab_swap'), icon: ArrowLeftRight, count: swapCount?.count },
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
                  {t('product_detail.teardown_title')}
                </h3>
                <div className="prose prose-invert max-w-none text-gray-300">
                  {product.teardown_notes}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Cpu className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>{t('product_detail.no_teardown')}</p>
                {isAuthenticated ? (
                  (user?.is_staff || product.created_by?.id === user?.id) && (
                    <button
                      onClick={() => setShowEditModal(true)}
                      className="text-cyber-cyan hover:underline text-sm mt-2 inline-block"
                    >
                      {t('product_detail.contribute_notes')}
                    </button>
                  )
                ) : (
                  <Link to="/login" className="text-cyber-cyan hover:underline text-sm mt-2 inline-block">
                    {t('product_detail.login_to_contribute')}
                  </Link>
                )}
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
                  {t('product_detail.images_title')} ({product.images.length})
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
                      <div className="aspect-[4/3] bg-cyber-black mb-2">
                        <LazyImage
                          src={img.thumbnail || img.image}
                          alt={img.caption || `Image ${idx + 1}`}
                          className="w-full h-full object-cover bg-cyber-black"
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
                      <div onClick={(e) => e.stopPropagation()}>
                        <RetroactiveBgRemoval
                          image={img}
                          kind="product"
                          onApplied={() => queryClient.invalidateQueries({ queryKey: ['product', id] })}
                        />
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
                  {t('product_detail.upload_images_title')}
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
                  {t('product_detail.login_to_upload_images')}
                </p>
                <Link to="/login" className="btn-cyber">
                  {t('product_detail.login_to_contribute')}
                </Link>
              </div>
            )}

            {/* Guidelines */}
            <div className="p-4 border border-cyber-light/20 bg-cyber-dark/50">
              <h4 className="font-mono text-sm text-cyber-cyan mb-2">{t('product_detail.img_guidelines_title')}</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• {t('product_detail.img_guideline_1')}</li>
                <li>• {t('product_detail.img_guideline_2')}</li>
                <li>• {t('product_detail.img_guideline_3')}</li>
                <li>• {t('product_detail.img_guideline_4')}</li>
                <li>• {t('product_detail.img_guideline_5')}</li>
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
                    {t('product_detail.documented_components')} ({componentList.length})
                  </h3>
                  {isAuthenticated && !showAddComponent && !showBomImport && !showBomPdfExtract && !showBatchAdd && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowBomImport(true)}
                        className="btn-cyber btn-cyber-green text-sm py-1.5"
                      >
                        {t('product_detail.import_bom')}
                      </button>
                      <button
                        onClick={() => setShowBomPdfExtract(true)}
                        className="btn-cyber text-sm py-1.5"
                      >
                        {t('product_detail.extract_from_manual')}
                      </button>
                      <button
                        onClick={() => setShowBatchAdd(true)}
                        className="btn-cyber text-sm py-1.5"
                      >
                        {t('product_detail.batch_add')}
                      </button>
                      <button
                        onClick={() => setShowAddComponent(true)}
                        className="btn-cyber text-sm py-1.5"
                      >
                        {t('product_detail.add_plus')}
                      </button>
                    </div>
                  )}
                </div>
                {/* Desktop table view */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-cyber-light/30 text-left">
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_ref')}</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_part')}</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_value')}</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_manufacturer')}</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_type')}</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_qty')}</th>
                        <th className="py-3 px-4 font-mono text-xs text-gray-500">{t('product_detail.col_notes')}</th>
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
                          <td className="py-3 px-4">
                            <ComponentVoteButtons pc={pc} productId={id!} />
                          </td>
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
                      <div className="flex items-center justify-between gap-2 mt-2">
                        <div className="flex items-center gap-2">
                          <span className="badge-cyber text-cyber-pink border-cyber-pink/50 text-[10px]">
                            {pc.component.component_type_display || pc.component.component_type}
                          </span>
                          {pc.quantity > 1 && (
                            <span className="text-xs text-gray-500">×{pc.quantity}</span>
                          )}
                        </div>
                        <ComponentVoteButtons pc={pc} productId={id!} compact />
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
                  {t('product_detail.add_component')}
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

            {/* Extract BOM from Manual PDF */}
            {isAuthenticated && showBomPdfExtract && (
              <div className="card-cyber p-6">
                <BomPdfExtract
                  productId={id!}
                  onClose={() => setShowBomPdfExtract(false)}
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
            {(!componentList || componentList.length === 0) && !showAddComponent && !showBomImport && !showBomPdfExtract && !showBatchAdd && (
              <div className="card-cyber p-8 text-center">
                <Cpu className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 mb-4">{t('product_detail.bom_empty')}</p>
                {isAuthenticated ? (
                  <div className="flex items-center justify-center gap-3">
                    <button
                      onClick={() => setShowBomImport(true)}
                      className="btn-cyber btn-cyber-green"
                    >
                      {t('product_detail.import_bom')}
                    </button>
                    <button
                      onClick={() => setShowBomPdfExtract(true)}
                      className="btn-cyber"
                    >
                      {t('product_detail.extract_from_manual')}
                    </button>
                    <button
                      onClick={() => setShowBatchAdd(true)}
                      className="btn-cyber"
                    >
                      {t('product_detail.batch_add')}
                    </button>
                    <button
                      onClick={() => setShowAddComponent(true)}
                      className="btn-cyber"
                    >
                      {t('product_detail.add_component')}
                    </button>
                  </div>
                ) : (
                  <Link to="/login" className="btn-cyber">
                    {t('product_detail.login_to_add_components')}
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
              <h4 className="font-mono text-sm text-cyber-pink mb-2">{t('product_detail.comp_guidelines_title')}</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• {t('product_detail.comp_guideline_1')}</li>
                <li>• {t('product_detail.comp_guideline_2')}</li>
                <li>• {t('product_detail.comp_guideline_3')}</li>
                <li>• {t('product_detail.comp_guideline_4')}</li>
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
                  {t('product_detail.available_schematics')} ({schematicList.length})
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
                        <div className="flex items-center gap-2">
                          {isAuthenticated && schematic.file_type === 'pdf' && BOM_EXTRACTABLE_SCHEMATIC_TYPES.includes(schematic.schematic_type) && (
                            <button
                              onClick={() => { setExtractingMode('text'); setExtractingSchematic(schematic); }}
                              title={t('product_detail.extract_from_manual')}
                              className="btn-cyber py-2 px-3"
                            >
                              <Sparkles className="h-4 w-4" />
                            </button>
                          )}
                          {isAuthenticated
                            && ['pdf', 'png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp'].includes(schematic.file_type)
                            && OCR_EXTRACTABLE_SCHEMATIC_TYPES.includes(schematic.schematic_type) && (
                            <button
                              onClick={() => { setExtractingMode('ocr'); setExtractingSchematic(schematic); }}
                              title={t('product_detail.ocr_scan_schematic')}
                              className="btn-cyber py-2 px-3"
                            >
                              <ScanText className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={async () => {
                              try {
                                const { download_url } = await schematics.download(schematic.id);
                                window.open(download_url, '_blank', 'noopener,noreferrer');
                              } catch {
                                // Fallback to direct URL if tracking endpoint fails
                                window.open(schematic.file_url, '_blank', 'noopener,noreferrer');
                              }
                            }}
                            className="btn-cyber btn-cyber-green py-2 px-3"
                          >
                            <Download className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      {extractingSchematic?.id === schematic.id && (
                        <div className="mt-4 pt-4 border-t border-cyber-light/20">
                          <BomPdfExtract
                            productId={id!}
                            schematicId={schematic.id}
                            schematicTitle={schematic.title}
                            mode={extractingMode}
                            onClose={() => setExtractingSchematic(null)}
                          />
                        </div>
                      )}
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
                  {t('product_detail.add_schematic')}
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
                  {t('product_detail.login_to_upload_schematics')}
                </p>
                <Link to="/login" className="btn-cyber">
                  {t('product_detail.login_to_contribute')}
                </Link>
              </div>
            )}

            {/* Empty state for no schematics */}
            {(!schematicList || schematicList.length === 0) && !isAuthenticated && (
              <div className="card-cyber p-8 text-center text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>{t('product_detail.no_schematics')}</p>
              </div>
            )}

            {/* Guidelines */}
            <div className="p-4 border border-cyber-light/20 bg-cyber-dark/50">
              <h4 className="font-mono text-sm text-cyber-green mb-2">{t('product_detail.sch_guidelines_title')}</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• {t('product_detail.sch_guideline_1')}</li>
                <li>• {t('product_detail.sch_guideline_2')}</li>
                <li>• {t('product_detail.sch_guideline_3')}</li>
                <li>• {t('product_detail.sch_guideline_4')}</li>
                <li>• {t('product_detail.sch_guideline_5')}</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'firmware' && (
          <div className="space-y-6">
            {/* Existing Firmware */}
            {firmwareList && firmwareList.length > 0 && (
              <div>
                <h3 className="font-display text-lg font-semibold text-white mb-4">
                  {t('product_detail.available_firmware')} ({firmwareList.length})
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {firmwareList.map((fw) => (
                    <div key={fw.id} className="card-cyber p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="badge-cyber text-cyber-green border-cyber-green text-[10px] mb-2">
                            {fw.source_type_display || fw.source_type}
                          </span>
                          <h4 className="font-semibold text-white">{fw.title}</h4>
                          {fw.chip_architecture && (
                            <p className="text-xs text-cyber-cyan font-mono mt-1">{fw.chip_architecture}</p>
                          )}
                          {fw.description && (
                            <p className="text-sm text-gray-400 mt-1">{fw.description}</p>
                          )}
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <span>{fw.file_type?.toUpperCase()}</span>
                            {fw.version && <span>v{fw.version}</span>}
                            {fw.file_size && (
                              <span>{(fw.file_size / 1024 / 1024).toFixed(1)} MB</span>
                            )}
                            <span>{fw.download_count} downloads</span>
                          </div>
                        </div>
                        <button
                          onClick={async () => {
                            try {
                              const { download_url } = await firmware.download(fw.id);
                              window.open(download_url, '_blank', 'noopener,noreferrer');
                            } catch {
                              // Fallback to direct URL if tracking endpoint fails
                              window.open(fw.file_url, '_blank', 'noopener,noreferrer');
                            }
                          }}
                          className="btn-cyber btn-cyber-green py-2 px-3"
                        >
                          <Download className="h-4 w-4" />
                        </button>
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
                  {t('product_detail.add_firmware')}
                </h3>
                <FirmwareUpload
                  productId={id!}
                  onSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: ['product', id, 'firmware'] });
                  }}
                />
              </div>
            ) : (
              <div className="card-cyber p-8 text-center">
                <HardDrive className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 mb-4">
                  {t('product_detail.login_to_upload_firmware')}
                </p>
                <Link to="/login" className="btn-cyber">
                  {t('product_detail.login_to_contribute')}
                </Link>
              </div>
            )}

            {/* Empty state for no firmware */}
            {(!firmwareList || firmwareList.length === 0) && !isAuthenticated && (
              <div className="card-cyber p-8 text-center text-gray-500">
                <HardDrive className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>{t('product_detail.no_firmware')}</p>
              </div>
            )}

            {/* Guidelines */}
            <div className="p-4 border border-cyber-light/20 bg-cyber-dark/50">
              <h4 className="font-mono text-sm text-cyber-green mb-2">{t('product_detail.fw_guidelines_title')}</h4>
              <ul className="text-xs text-gray-500 space-y-1">
                <li>• {t('product_detail.fw_guideline_1')}</li>
                <li>• {t('product_detail.fw_guideline_2')}</li>
                <li>• {t('product_detail.fw_guideline_3')}</li>
                <li>• {t('product_detail.fw_guideline_4')}</li>
                <li>• {t('product_detail.fw_guideline_5')}</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'comments' && (
          <ProductComments productId={id!} />
        )}

        {activeTab === 'swap' && (
          <div className="space-y-8">
            {/* HAVE section */}
            <div>
              <h3 className="font-display text-lg font-semibold text-white mb-4">
                {t('product_detail.have')} <span className="text-cyber-cyan text-sm font-mono">({swapHave?.count ?? 0})</span>
              </h3>
              {swapHave?.results?.length ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {swapHave.results.map((item) => (
                    <SwapItemCard
                      key={item.id}
                      item={item}
                      currentUserId={user?.id}
                      isAuthenticated={isAuthenticated}
                      t={t}
                    />
                  ))}
                </div>
              ) : (
                <div className="card-cyber p-8 text-center">
                  <p className="text-gray-500 font-mono text-sm">{t('product_detail.swap_no_items')}</p>
                  {isAuthenticated && (
                    <button
                      onClick={() => setShowJunkbinModal(true)}
                      className="text-cyber-cyan hover:underline text-sm mt-2 font-mono"
                    >
                      {t('product_detail.add_to_junkbin')}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* WANT section */}
            <div>
              <h3 className="font-display text-lg font-semibold text-white mb-4">
                {t('product_detail.want')} <span className="text-cyber-yellow text-sm font-mono">({swapWant?.count ?? 0})</span>
              </h3>
              {swapWant?.results?.length ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {swapWant.results.map((item) => (
                    <SwapItemCard
                      key={item.id}
                      item={item}
                      currentUserId={user?.id}
                      isAuthenticated={isAuthenticated}
                      t={t}
                    />
                  ))}
                </div>
              ) : (
                <div className="card-cyber p-8 text-center">
                  <p className="text-gray-500 font-mono text-sm">{t('product_detail.swap_no_items')}</p>
                </div>
              )}
            </div>
          </div>
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

      {/* Add to My Junkbin Modal */}
      <AddToJunkbinModal
        isOpen={showJunkbinModal}
        onClose={() => setShowJunkbinModal(false)}
        contentType="product"
        objectId={id!}
        itemName={`${product?.manufacturer} ${product?.model_number}`}
      />

      {/* Edit Product Modal */}
      {product && (
        <EditProductModal
          product={product}
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          isStaff={user?.is_staff || false}
        />
      )}

      {/* Lightbox */}
      {lightboxIndex !== null && product.images && product.images.length > 0 && (
        <Lightbox
          images={product.images.map((img) => ({
            src: img.image,
            caption: img.caption || img.image_type_display || '',
          }))}
          initialIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </div>
  );
}
