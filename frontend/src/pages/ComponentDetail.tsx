import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { components, junkbin } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import AddToJunkbinModal from '../components/AddToJunkbinModal';
import EditComponentModal from '../components/EditComponentModal';
import PricingPanel from '../components/PricingPanel';
import ImageUpload, { COMPONENT_IMAGE_TYPES } from '../components/ImageUpload';
import DatasheetUpload from '../components/DatasheetUpload';
import Lightbox from '../components/Lightbox';
import { ArrowLeft, Cpu, ExternalLink, CheckCircle, Package, Archive, ImagePlus, Pencil, FileText, Download, BookOpen, MessageSquare, Store } from 'lucide-react';
import type { JunkbinItem } from '../types';

function CompactSwapCard({ item, currentUserId, isAuthenticated }: {
  item: JunkbinItem;
  currentUserId?: string;
  isAuthenticated: boolean;
}) {
  const canContact =
    isAuthenticated && currentUserId !== item.user.id && item.item_type === 'have' && item.status === 'available';
  return (
    <div className="card-cyber p-3 flex flex-col gap-2 min-w-[180px]">
      <div className="flex items-center gap-2 flex-wrap">
        {item.item_type === 'have' && (
          <span className={item.status === 'available'
            ? 'badge-cyber text-[10px] text-cyber-green border-cyber-green'
            : 'badge-cyber text-[10px] text-gray-500 border-gray-600'
          }>
            {item.status === 'available' ? 'AVAIL' : 'NOT FOR TRADE'}
          </span>
        )}
        {item.item_type === 'have' && (
          <span className="badge-cyber text-[10px] text-gray-400 border-gray-600">
            {{ new: 'New', working: 'Working', broken: 'Broken', unknown: 'Unknown' }[item.condition] || item.condition}
          </span>
        )}
        {item.quantity > 1 && (
          <span className="text-xs text-gray-500 font-mono">×{item.quantity}</span>
        )}
      </div>
      {item.notes && (
        <p className="text-xs text-gray-400 line-clamp-2">{item.notes}</p>
      )}
      <div className="flex items-center justify-between gap-2 pt-1 border-t border-cyber-light/20">
        <Link to={`/users/${item.user.id}`} className="flex items-center gap-1.5 group min-w-0">
          <div className="w-5 h-5 rounded-full bg-cyber-gray border border-cyber-light/30 flex items-center justify-center overflow-hidden flex-shrink-0">
            {item.user.avatar ? (
              <img src={item.user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              <span className="text-gray-500 font-mono text-[9px]">
                {item.user.username.charAt(0).toUpperCase()}
              </span>
            )}
          </div>
          <span className="text-[11px] text-gray-400 group-hover:text-cyber-cyan transition-colors font-mono truncate">
            {item.user.display_name || item.user.username}
          </span>
        </Link>
        {canContact && (
          <Link
            to={`/messages/new?user=${item.user.id}`}
            className="text-cyber-cyan hover:text-white transition-colors flex-shrink-0"
            title="Contact"
          >
            <MessageSquare className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>
    </div>
  );
}

export default function ComponentDetail() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, user } = useAuth();
  const [showJunkbinModal, setShowJunkbinModal] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [showDatasheetUpload, setShowDatasheetUpload] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const { data: component, isLoading: componentLoading } = useQuery({
    queryKey: ['component', id],
    queryFn: () => components.get(id!),
    enabled: !!id,
  });

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ['component-products', id],
    queryFn: () => components.crossReference(id!),
    enabled: !!id,
  });

  const { data: swapItems } = useQuery({
    queryKey: ['junkbin', 'component', id],
    queryFn: () => junkbin.list({ content_type: 'component', object_id: id }),
    enabled: !!id,
  });

  const isLoading = componentLoading || productsLoading;

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-cyber-pink font-mono animate-pulse">
          LOADING CROSS-REFERENCE DATA...
        </div>
      </div>
    );
  }

  if (!component) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <Package className="h-16 w-16 text-gray-600 mb-4" />
        <h2 className="font-display text-xl text-white mb-2">COMPONENT NOT FOUND</h2>
        <Link to="/components" className="text-cyber-pink hover:text-white transition-colors">
          ← Back to Components
        </Link>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-screen-2xl px-4">
        {/* Back link */}
        <Link
          to="/components"
          className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Components
        </Link>

        {/* Component Info Card */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-6">
            {/* Image / Icon */}
            <div className="w-24 h-24 bg-cyber-black flex items-center justify-center border border-cyber-light/20 flex-shrink-0 overflow-hidden">
              {component.primary_image ? (
                <img
                  src={component.primary_image.thumbnail || component.primary_image.image}
                  alt={component.part_number}
                  className="w-full h-full object-cover"
                />
              ) : (
                <Package className="h-12 w-12 text-cyber-pink/60" />
              )}
            </div>

            {/* Info */}
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm font-mono text-cyber-pink">
                  {component.manufacturer}
                </span>
                {component.is_verified && (
                  <span className="flex items-center gap-1 text-xs text-cyber-green">
                    <CheckCircle className="h-3.5 w-3.5" />
                    Verified
                  </span>
                )}
              </div>

              <h1 className="font-display text-2xl md:text-3xl font-bold text-white mb-2">
                {component.part_number}
              </h1>

              <div className="flex flex-wrap gap-3 mb-4">
                <span className="badge-cyber text-cyber-pink border-cyber-pink">
                  {component.component_type_display || component.component_type}
                </span>
                {component.package_type && (
                  <span className="badge-cyber text-gray-400 border-gray-600">
                    {component.package_type}
                  </span>
                )}
              </div>

              {component.description && (
                <p className="text-gray-400 mb-4">{component.description}</p>
              )}

              <div className="flex flex-wrap items-center gap-4 mt-2">
                {component.datasheet_url && (
                  <a
                    href={component.datasheet_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-cyber-cyan hover:text-white transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View Datasheet
                  </a>
                )}
                {isAuthenticated && (
                  <button
                    onClick={() => setShowJunkbinModal(true)}
                    className="inline-flex items-center gap-2 text-gray-400 hover:text-cyber-cyan transition-colors text-sm"
                  >
                    <Archive className="h-4 w-4" />
                    Add to My Junkbin
                  </button>
                )}
                {isAuthenticated && (
                  <button
                    onClick={() => setShowUpload(!showUpload)}
                    className="inline-flex items-center gap-2 text-gray-400 hover:text-cyber-cyan transition-colors text-sm"
                  >
                    <ImagePlus className="h-4 w-4" />
                    {showUpload ? 'Hide Upload' : 'Upload Image'}
                  </button>
                )}
                {isAuthenticated && (
                  <button
                    onClick={() => setShowDatasheetUpload(!showDatasheetUpload)}
                    className="inline-flex items-center gap-2 text-gray-400 hover:text-cyber-cyan transition-colors text-sm"
                  >
                    <BookOpen className="h-4 w-4" />
                    {showDatasheetUpload ? 'Hide Upload' : 'Upload Datasheet'}
                  </button>
                )}
                {isAuthenticated && (user?.is_staff || component.created_by?.id === user?.id) && (
                  <button
                    onClick={() => setShowEditModal(true)}
                    className="inline-flex items-center gap-2 text-gray-400 hover:text-cyber-cyan transition-colors text-sm"
                  >
                    <Pencil className="h-4 w-4" />
                    Edit
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Image gallery */}
          {component.images && component.images.length > 0 && (
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {component.images.map((img, idx) => (
                <button
                  key={img.id}
                  onClick={() => setLightboxIndex(idx)}
                  className="aspect-video bg-cyber-black border border-cyber-light/20 overflow-hidden hover:border-cyber-pink/50 transition-colors cursor-zoom-in"
                >
                  <img
                    src={img.medium || img.image}
                    alt={img.caption || component.part_number}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}

          {/* Lightbox */}
          {lightboxIndex !== null && component.images && (
            <Lightbox
              images={component.images.map((img) => ({
                src: img.image,
                caption: img.caption || img.image_type_display || '',
              }))}
              initialIndex={lightboxIndex}
              onClose={() => setLightboxIndex(null)}
            />
          )}

          {/* Image upload section */}
          {showUpload && isAuthenticated && (
            <div className="mt-6">
              <ImageUpload
                uploadFn={(formData) => components.uploadImage(id!, formData)}
                invalidateKey={['component', id!]}
                imageTypes={COMPONENT_IMAGE_TYPES}
                onSuccess={() => setShowUpload(false)}
              />
            </div>
          )}

          {/* Datasheet upload section */}
          {showDatasheetUpload && isAuthenticated && (
            <div className="mt-6">
              <h3 className="font-display text-sm font-bold text-white mb-3">UPLOAD DATASHEET</h3>
              <DatasheetUpload
                uploadFn={(formData) => components.uploadDatasheet(id!, formData)}
                invalidateKey={['component', id!]}
                onSuccess={() => setShowDatasheetUpload(false)}
              />
            </div>
          )}
        </div>

        {/* Pricing & Availability */}
        <div className="mb-8">
          <PricingPanel
            componentId={id!}
            pricingData={component.pricing_data}
            datasheetUrl={component.datasheet_url}
          />
        </div>

        {/* Datasheets */}
        {component.datasheets && component.datasheets.length > 0 && (
          <div className="mb-8">
            <h2 className="font-display text-xl font-bold text-white mb-4">
              DATASHEETS
            </h2>
            <div className="space-y-2">
              {component.datasheets.map((ds) => (
                <div
                  key={ds.id}
                  className="card-cyber p-4 flex items-center gap-4"
                >
                  <FileText className="h-5 w-5 text-cyber-cyan flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-0.5">
                      <span className="text-white font-medium truncate">{ds.title}</span>
                      {ds.version && (
                        <span className="badge-cyber text-cyber-cyan border-cyber-cyan text-xs">
                          {ds.version}
                        </span>
                      )}
                      <span className="badge-cyber text-gray-400 border-gray-600 text-xs uppercase">
                        {ds.file_type}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 font-mono">
                      {ds.file_size && (
                        <span>{(ds.file_size / 1024).toFixed(0)} KB</span>
                      )}
                      <span>{ds.source_type}</span>
                      {ds.uploaded_by && <span>by {ds.uploaded_by.username}</span>}
                      <span>{ds.download_count} downloads</span>
                    </div>
                  </div>
                  <a
                    href={ds.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-cyber-cyan hover:text-white transition-colors text-sm flex-shrink-0"
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* WHO HAS THIS? — only shown if there are any junkbin items */}
        {swapItems && swapItems.count > 0 && (() => {
          const haveItems = swapItems.results.filter((i) => i.item_type === 'have');
          const wantItems = swapItems.results.filter((i) => i.item_type === 'want');
          return (
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-4">
                <Store className="h-5 w-5 text-cyber-cyan" />
                <h2 className="font-display text-xl font-bold text-white">
                  WHO HAS THIS?
                </h2>
                <Link to={`/swap?content_type=component`} className="text-xs text-gray-500 hover:text-cyber-cyan font-mono transition-colors">
                  → SWAP SHOP
                </Link>
              </div>

              {haveItems.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-mono text-xs text-cyber-cyan uppercase mb-2">
                    HAVE ({haveItems.length})
                  </h3>
                  <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
                    {haveItems.map((item) => (
                      <CompactSwapCard
                        key={item.id}
                        item={item}
                        currentUserId={user?.id}
                        isAuthenticated={isAuthenticated}
                      />
                    ))}
                  </div>
                </div>
              )}

              {wantItems.length > 0 && (
                <div>
                  <h3 className="font-mono text-xs text-cyber-yellow uppercase mb-2">
                    WANT ({wantItems.length})
                  </h3>
                  <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
                    {wantItems.map((item) => (
                      <CompactSwapCard
                        key={item.id}
                        item={item}
                        currentUserId={user?.id}
                        isAuthenticated={isAuthenticated}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* Products containing this component */}
        <div>
          <h2 className="font-display text-xl font-bold text-white mb-4">
            PRODUCTS CONTAINING <span className="text-cyber-pink">{component.part_number}</span>
          </h2>

          <p className="text-gray-500 text-sm mb-6 font-mono">
            {products?.length || 0} products found
          </p>

          {products && products.length > 0 ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {products.map((product: any) => (
                <Link
                  key={product.id}
                  to={`/products/${product.id}`}
                  className="card-cyber p-4 hover:border-cyber-cyan/50 transition-all group"
                >
                  {/* Image */}
                  <div className="aspect-[4/3] mb-4 bg-cyber-black flex items-center justify-center border border-cyber-light/20">
                    {product.primary_image ? (
                      <img
                        src={product.primary_image.thumbnail || product.primary_image.image}
                        alt={product.model_number}
                        className="w-full h-full object-cover bg-cyber-black"
                      />
                    ) : (
                      <Cpu className="h-8 w-8 text-gray-600" />
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-cyber-cyan">
                      {product.manufacturer}
                    </span>
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
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 card-cyber">
              <Cpu className="h-12 w-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500">
                No products documented with this component yet.
              </p>
              <Link to="/submit" className="btn-cyber mt-4 inline-block">
                ADD A PRODUCT
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Add to My Junkbin Modal */}
      <AddToJunkbinModal
        isOpen={showJunkbinModal}
        onClose={() => setShowJunkbinModal(false)}
        contentType="component"
        objectId={id!}
        itemName={`${component.manufacturer} ${component.part_number}`}
      />

      {/* Edit Component Modal */}
      <EditComponentModal
        component={component}
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
      />
    </div>
  );
}
