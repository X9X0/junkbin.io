import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Cpu, Package, Upload, ChevronRight, ChevronLeft, Check, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import BomTemplateDownload from '../components/BomTemplateDownload';
import { parseApiError } from '../utils/formErrors';

const CATEGORIES = [
  { value: '', label: 'Select Category' },
  { value: 'desktop', label: 'Desktop Computer' },
  { value: 'laptop', label: 'Laptop/Notebook' },
  { value: 'tablet', label: 'Tablet' },
  { value: 'phone', label: 'Smartphone' },
  { value: 'tv', label: 'Television' },
  { value: 'monitor', label: 'Monitor' },
  { value: 'router', label: 'Router' },
  { value: 'modem', label: 'Modem' },
  { value: 'switch', label: 'Network Switch' },
  { value: 'access_point', label: 'Access Point' },
  { value: 'audio', label: 'Audio Equipment' },
  { value: 'speaker', label: 'Speaker/Soundbar' },
  { value: 'gaming', label: 'Gaming Console' },
  { value: 'handheld', label: 'Handheld Gaming' },
  { value: 'remote', label: 'Remote Control' },
  { value: 'power_supply', label: 'Power Supply' },
  { value: 'charger', label: 'Charger' },
  { value: 'iot', label: 'IoT Device' },
  { value: 'smart_home', label: 'Smart Home Hub' },
  { value: 'camera', label: 'Camera' },
  { value: 'printer', label: 'Printer' },
  { value: 'other', label: 'Other' },
];

const REGIONS = [
  { value: 'global', label: 'Global/Universal' },
  { value: 'us', label: 'United States' },
  { value: 'eu', label: 'European Union' },
  { value: 'uk', label: 'United Kingdom' },
  { value: 'jp', label: 'Japan' },
  { value: 'cn', label: 'China' },
  { value: 'kr', label: 'South Korea' },
  { value: 'au', label: 'Australia' },
  { value: 'ca', label: 'Canada' },
  { value: 'other', label: 'Other' },
];

const COMPONENT_TYPES = [
  { value: '', label: 'Select Type' },
  { value: 'ic', label: 'Integrated Circuit' },
  { value: 'mcu', label: 'Microcontroller' },
  { value: 'transistor', label: 'Transistor' },
  { value: 'mosfet', label: 'MOSFET' },
  { value: 'diode', label: 'Diode' },
  { value: 'regulator', label: 'Voltage Regulator' },
  { value: 'opamp', label: 'Op-Amp' },
  { value: 'resistor', label: 'Resistor' },
  { value: 'capacitor', label: 'Capacitor' },
  { value: 'inductor', label: 'Inductor' },
  { value: 'transformer', label: 'Transformer' },
  { value: 'crystal', label: 'Crystal/Oscillator' },
  { value: 'relay', label: 'Relay' },
  { value: 'switch', label: 'Switch' },
  { value: 'connector', label: 'Connector' },
  { value: 'led', label: 'LED' },
  { value: 'display', label: 'Display/LCD' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'module', label: 'Module' },
  { value: 'other', label: 'Other' },
];

type SubmitType = 'product' | 'component';

interface ProductFormData {
  manufacturer: string;
  model_number: string;
  revision: string;
  region: string;
  category: string;
  year_manufactured: string;
  fcc_id: string;
  description: string;
  teardown_notes: string;
}

interface ComponentFormData {
  part_number: string;
  manufacturer: string;
  component_type: string;
  package_type: string;
  description: string;
  typical_function: string;
  datasheet_url: string;
}

export default function Submit() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [submitType, setSubmitType] = useState<SubmitType>('product');
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  // Product form state
  const [productData, setProductData] = useState<ProductFormData>({
    manufacturer: '',
    model_number: '',
    revision: '',
    region: 'global',
    category: '',
    year_manufactured: '',
    fcc_id: '',
    description: '',
    teardown_notes: '',
  });

  // Component form state
  const [componentData, setComponentData] = useState<ComponentFormData>({
    part_number: '',
    manufacturer: '',
    component_type: '',
    package_type: '',
    description: '',
    typical_function: '',
    datasheet_url: '',
  });

  // Mutations
  const productMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const response = await products.create(data);
      return response;
    },
    onSuccess: (data) => {
      navigate(`/products/${data.id}`);
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to create product. Please try again.'));
    },
  });

  const componentMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const response = await api.post('/components/', data);
      return response.data;
    },
    onSuccess: (data) => {
      navigate(`/components/${data.id}/products`);
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to create component. Please try again.'));
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <AlertCircle className="h-16 w-16 text-cyber-pink mb-4" />
        <h2 className="font-display text-2xl text-white mb-2">AUTHENTICATION REQUIRED</h2>
        <p className="text-gray-400 mb-6 text-center">
          You must be logged in to submit products or components.
        </p>
        <a href="/login" className="btn-cyber">
          LOGIN TO CONTINUE
        </a>
      </div>
    );
  }

  const handleProductChange = (field: keyof ProductFormData, value: string) => {
    setProductData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleComponentChange = (field: keyof ComponentFormData, value: string) => {
    setComponentData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmitProduct = () => {
    const data: any = { ...productData };
    if (data.year_manufactured) {
      data.year_manufactured = parseInt(data.year_manufactured, 10);
    } else {
      delete data.year_manufactured;
    }
    // Remove empty strings
    Object.keys(data).forEach((key) => {
      if (data[key] === '') delete data[key];
    });
    productMutation.mutate(data);
  };

  const handleSubmitComponent = () => {
    const data: any = { ...componentData };
    // Remove empty strings
    Object.keys(data).forEach((key) => {
      if (data[key] === '') delete data[key];
    });
    componentMutation.mutate(data);
  };

  const isProductStep1Valid = productData.manufacturer && productData.model_number && productData.category;
  const isComponentStep1Valid = componentData.manufacturer && componentData.part_number && componentData.component_type;

  return (
    <div className="py-8">
      <div className="mx-auto max-w-3xl px-4">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            SUBMIT <span className="text-cyber-green">DOCUMENTATION</span>
          </h1>
          <p className="text-gray-400">
            Help build the e-waste salvage database
          </p>
        </div>

        {/* Type Selector */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => {
              setSubmitType('product');
              setStep(1);
              setError(null);
            }}
            className={clsx(
              'flex-1 p-4 border-2 transition-all flex flex-col items-center gap-2',
              submitType === 'product'
                ? 'border-cyber-cyan bg-cyber-cyan/10 text-cyber-cyan'
                : 'border-cyber-light/30 text-gray-500 hover:border-cyber-light/50'
            )}
          >
            <Cpu className="h-8 w-8" />
            <span className="font-display font-bold">PRODUCT</span>
            <span className="text-xs text-gray-500">Document a device</span>
          </button>
          <button
            onClick={() => {
              setSubmitType('component');
              setStep(1);
              setError(null);
            }}
            className={clsx(
              'flex-1 p-4 border-2 transition-all flex flex-col items-center gap-2',
              submitType === 'component'
                ? 'border-cyber-pink bg-cyber-pink/10 text-cyber-pink'
                : 'border-cyber-light/30 text-gray-500 hover:border-cyber-light/50'
            )}
          >
            <Package className="h-8 w-8" />
            <span className="font-display font-bold">COMPONENT</span>
            <span className="text-xs text-gray-500">Add a part</span>
          </button>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={clsx(
                  'w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-sm transition-all',
                  step > s
                    ? 'border-cyber-green bg-cyber-green text-black'
                    : step === s
                    ? submitType === 'product'
                      ? 'border-cyber-cyan text-cyber-cyan'
                      : 'border-cyber-pink text-cyber-pink'
                    : 'border-cyber-light/30 text-gray-600'
                )}
              >
                {step > s ? <Check className="h-4 w-4" /> : s}
              </div>
              {s < 3 && (
                <div
                  className={clsx(
                    'w-12 h-0.5 mx-2',
                    step > s ? 'bg-cyber-green' : 'bg-cyber-light/30'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
            {error}
          </div>
        )}

        {/* Product Form */}
        {submitType === 'product' && (
          <div className="card-cyber p-6">
            {step === 1 && (
              <div className="space-y-6">
                <h2 className="font-display text-lg text-white mb-4">
                  BASIC INFORMATION
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      MANUFACTURER *
                    </label>
                    <input
                      type="text"
                      value={productData.manufacturer}
                      onChange={(e) => handleProductChange('manufacturer', e.target.value)}
                      placeholder="e.g., Samsung, Cisco, Apple"
                      className="input-cyber"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      MODEL NUMBER *
                    </label>
                    <input
                      type="text"
                      value={productData.model_number}
                      onChange={(e) => handleProductChange('model_number', e.target.value)}
                      placeholder="e.g., RT-AX88U, iPhone 12"
                      className="input-cyber"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      CATEGORY *
                    </label>
                    <select
                      value={productData.category}
                      onChange={(e) => handleProductChange('category', e.target.value)}
                      className="input-cyber"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      REGION
                    </label>
                    <select
                      value={productData.region}
                      onChange={(e) => handleProductChange('region', e.target.value)}
                      className="input-cyber"
                    >
                      {REGIONS.map((reg) => (
                        <option key={reg.value} value={reg.value}>
                          {reg.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h2 className="font-display text-lg text-white mb-4">
                  ADDITIONAL DETAILS
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      REVISION
                    </label>
                    <input
                      type="text"
                      value={productData.revision}
                      onChange={(e) => handleProductChange('revision', e.target.value)}
                      placeholder="e.g., v1.2, Rev A"
                      className="input-cyber"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      YEAR MANUFACTURED
                    </label>
                    <input
                      type="number"
                      value={productData.year_manufactured}
                      onChange={(e) => handleProductChange('year_manufactured', e.target.value)}
                      placeholder="e.g., 2023"
                      min="1970"
                      max="2030"
                      className="input-cyber"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      FCC ID
                    </label>
                    <input
                      type="text"
                      value={productData.fcc_id}
                      onChange={(e) => handleProductChange('fcc_id', e.target.value)}
                      placeholder="e.g., MSQ-RTAX88U"
                      className="input-cyber"
                    />
                    <p className="text-xs text-gray-600 mt-1">
                      Found on device label. Search at fcc.gov/oet/ea/fccid
                    </p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-mono text-gray-400 mb-2">
                    DESCRIPTION
                  </label>
                  <textarea
                    value={productData.description}
                    onChange={(e) => handleProductChange('description', e.target.value)}
                    placeholder="Brief description of the product..."
                    rows={3}
                    className="input-cyber resize-none"
                  />
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6">
                <h2 className="font-display text-lg text-white mb-4">
                  REVIEW & SUBMIT
                </h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Manufacturer:</span>
                      <p className="text-white font-mono">{productData.manufacturer}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Model:</span>
                      <p className="text-white font-mono">{productData.model_number}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Category:</span>
                      <p className="text-white font-mono">
                        {CATEGORIES.find((c) => c.value === productData.category)?.label}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Region:</span>
                      <p className="text-white font-mono">
                        {REGIONS.find((r) => r.value === productData.region)?.label}
                      </p>
                    </div>
                    {productData.revision && (
                      <div>
                        <span className="text-gray-500">Revision:</span>
                        <p className="text-white font-mono">{productData.revision}</p>
                      </div>
                    )}
                    {productData.fcc_id && (
                      <div>
                        <span className="text-gray-500">FCC ID:</span>
                        <p className="text-white font-mono">{productData.fcc_id}</p>
                      </div>
                    )}
                  </div>
                  {productData.description && (
                    <div>
                      <span className="text-gray-500 text-sm">Description:</span>
                      <p className="text-gray-300 text-sm mt-1">{productData.description}</p>
                    </div>
                  )}
                </div>
                <div className="border-t border-cyber-light/30 pt-4">
                  <p className="text-xs text-gray-500">
                    After submission, you can add images and component documentation to this product.
                  </p>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-8 pt-6 border-t border-cyber-light/30">
              {step > 1 ? (
                <button
                  onClick={() => setStep(step - 1)}
                  className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                  BACK
                </button>
              ) : (
                <div />
              )}
              {step < 3 ? (
                <button
                  onClick={() => setStep(step + 1)}
                  disabled={step === 1 && !isProductStep1Valid}
                  className={clsx(
                    'btn-cyber flex items-center gap-2',
                    step === 1 && !isProductStep1Valid && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  NEXT
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmitProduct}
                  disabled={productMutation.isPending}
                  className="btn-cyber flex items-center gap-2"
                >
                  {productMutation.isPending ? (
                    'SUBMITTING...'
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      SUBMIT PRODUCT
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Component Form */}
        {submitType === 'component' && (
          <div className="card-cyber p-6">
            {step === 1 && (
              <div className="space-y-6">
                <h2 className="font-display text-lg text-white mb-4">
                  COMPONENT IDENTIFICATION
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      MANUFACTURER *
                    </label>
                    <input
                      type="text"
                      value={componentData.manufacturer}
                      onChange={(e) => handleComponentChange('manufacturer', e.target.value)}
                      placeholder="e.g., Texas Instruments, STMicro"
                      className="input-cyber"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      PART NUMBER *
                    </label>
                    <input
                      type="text"
                      value={componentData.part_number}
                      onChange={(e) => handleComponentChange('part_number', e.target.value)}
                      placeholder="e.g., LM7805, STM32F103"
                      className="input-cyber"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      COMPONENT TYPE *
                    </label>
                    <select
                      value={componentData.component_type}
                      onChange={(e) => handleComponentChange('component_type', e.target.value)}
                      className="input-cyber"
                    >
                      {COMPONENT_TYPES.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      PACKAGE TYPE
                    </label>
                    <input
                      type="text"
                      value={componentData.package_type}
                      onChange={(e) => handleComponentChange('package_type', e.target.value)}
                      placeholder="e.g., SOT-23, SOIC-8, QFP-48"
                      className="input-cyber"
                    />
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h2 className="font-display text-lg text-white mb-4">
                  ADDITIONAL DETAILS
                </h2>
                <div>
                  <label className="block text-sm font-mono text-gray-400 mb-2">
                    TYPICAL FUNCTION
                  </label>
                  <input
                    type="text"
                    value={componentData.typical_function}
                    onChange={(e) => handleComponentChange('typical_function', e.target.value)}
                    placeholder="e.g., 5V Linear Regulator, ARM Cortex-M3 MCU"
                    className="input-cyber"
                  />
                </div>
                <div>
                  <label className="block text-sm font-mono text-gray-400 mb-2">
                    DATASHEET URL
                  </label>
                  <input
                    type="url"
                    value={componentData.datasheet_url}
                    onChange={(e) => handleComponentChange('datasheet_url', e.target.value)}
                    placeholder="https://..."
                    className="input-cyber"
                  />
                </div>
                <div>
                  <label className="block text-sm font-mono text-gray-400 mb-2">
                    DESCRIPTION
                  </label>
                  <textarea
                    value={componentData.description}
                    onChange={(e) => handleComponentChange('description', e.target.value)}
                    placeholder="Brief description of the component..."
                    rows={3}
                    className="input-cyber resize-none"
                  />
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6">
                <h2 className="font-display text-lg text-white mb-4">
                  REVIEW & SUBMIT
                </h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Manufacturer:</span>
                      <p className="text-white font-mono">{componentData.manufacturer}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Part Number:</span>
                      <p className="text-white font-mono">{componentData.part_number}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Type:</span>
                      <p className="text-white font-mono">
                        {COMPONENT_TYPES.find((t) => t.value === componentData.component_type)?.label}
                      </p>
                    </div>
                    {componentData.package_type && (
                      <div>
                        <span className="text-gray-500">Package:</span>
                        <p className="text-white font-mono">{componentData.package_type}</p>
                      </div>
                    )}
                  </div>
                  {componentData.typical_function && (
                    <div>
                      <span className="text-gray-500 text-sm">Function:</span>
                      <p className="text-gray-300 text-sm mt-1">{componentData.typical_function}</p>
                    </div>
                  )}
                  {componentData.description && (
                    <div>
                      <span className="text-gray-500 text-sm">Description:</span>
                      <p className="text-gray-300 text-sm mt-1">{componentData.description}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-8 pt-6 border-t border-cyber-light/30">
              {step > 1 ? (
                <button
                  onClick={() => setStep(step - 1)}
                  className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                  BACK
                </button>
              ) : (
                <div />
              )}
              {step < 3 ? (
                <button
                  onClick={() => setStep(step + 1)}
                  disabled={step === 1 && !isComponentStep1Valid}
                  className={clsx(
                    'btn-cyber flex items-center gap-2',
                    step === 1 && !isComponentStep1Valid && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  NEXT
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmitComponent}
                  disabled={componentMutation.isPending}
                  className="btn-cyber flex items-center gap-2"
                >
                  {componentMutation.isPending ? (
                    'SUBMITTING...'
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      SUBMIT COMPONENT
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Info box */}
        <div className="mt-8 p-4 border border-cyber-light/20 bg-cyber-dark/50">
          <h3 className="font-mono text-sm text-cyber-cyan mb-2">CONTRIBUTION GUIDELINES</h3>
          <ul className="text-xs text-gray-500 space-y-1">
            <li>• Ensure accuracy - double-check part numbers and specifications</li>
            <li>• Include FCC IDs when available - they help with identification</li>
            <li>• High-quality photos will be requested after initial submission</li>
            <li>• Contributions may be reviewed before appearing publicly</li>
          </ul>
        </div>

        {/* BOM Template Download */}
        <div className="mt-6">
          <BomTemplateDownload />
        </div>
      </div>
    </div>
  );
}
