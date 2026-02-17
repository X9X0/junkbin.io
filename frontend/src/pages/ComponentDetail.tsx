import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { components } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import AddToJunkbinModal from '../components/AddToJunkbinModal';
import PricingPanel from '../components/PricingPanel';
import ImageUpload, { COMPONENT_IMAGE_TYPES } from '../components/ImageUpload';
import { ArrowLeft, Cpu, ExternalLink, CheckCircle, Package, Archive, ImagePlus } from 'lucide-react';

export default function ComponentDetail() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated } = useAuth();
  const [showJunkbinModal, setShowJunkbinModal] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

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
      <div className="mx-auto max-w-7xl px-4">
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
              {component.images && component.images.length > 0 ? (
                <img
                  src={component.images[0].thumbnail || component.images[0].image}
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
              </div>
            </div>
          </div>

          {/* Image gallery */}
          {component.images && component.images.length > 0 && (
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {component.images.map((img: any) => (
                <div key={img.id} className="aspect-video bg-cyber-black border border-cyber-light/20 overflow-hidden">
                  <img
                    src={img.medium || img.image}
                    alt={img.caption || component.part_number}
                    className="w-full h-full object-cover"
                  />
                </div>
              ))}
            </div>
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
        </div>

        {/* Pricing & Availability */}
        <div className="mb-8">
          <PricingPanel
            componentId={id!}
            pricingData={component.pricing_data}
            datasheetUrl={component.datasheet_url}
          />
        </div>

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
                  <div className="aspect-video mb-4 bg-cyber-black flex items-center justify-center border border-cyber-light/20">
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
    </div>
  );
}
