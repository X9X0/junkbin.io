import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Cpu, Package, Upload, ChevronRight, ChevronLeft, Check, AlertCircle, ExternalLink, Camera, FileText, X, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import BomTemplateDownload from '../components/BomTemplateDownload';
import ModerationNotice from '../components/ModerationNotice';
import { parseApiError } from '../utils/formErrors';
import { PRODUCT_CATEGORIES, REGIONS, COMPONENT_TYPES } from '../utils/constants';
import ImageUpload, { COMPONENT_IMAGE_TYPES } from '../components/ImageUpload';
import SchematicUpload from '../components/SchematicUpload';
import { components as componentsApi } from '../api/endpoints';

const CATEGORIES = PRODUCT_CATEGORIES;

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

interface SubmittedItem {
  type: SubmitType;
  id: string;
  label: string;
}

export default function Submit() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [submitType, setSubmitType] = useState<SubmitType>('product');
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [submittedItem, setSubmittedItem] = useState<SubmittedItem | null>(null);
  const [uploadsDone, setUploadsDone] = useState(false);
  const [uploadTab, setUploadTab] = useState<'photos' | 'docs'>('photos');
  // Component datasheet upload state
  const [dsFile, setDsFile] = useState<File | null>(null);
  const [dsTitle, setDsTitle] = useState('');
  const [dsSourceType, setDsSourceType] = useState('official');
  const [dsSourceUrl, setDsSourceUrl] = useState('');

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
      setSubmittedItem({
        type: 'product',
        id: data.id,
        label: `${data.manufacturer} ${data.model_number}`,
      });
    },
    onError: (err: any) => {
      setError(parseApiError(err, t('submit.error_product')));
    },
  });

  const componentMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const response = await api.post('/components/', data);
      return response.data;
    },
    onSuccess: (data) => {
      setSubmittedItem({
        type: 'component',
        id: data.id,
        label: `${data.manufacturer} ${data.part_number}`,
      });
    },
    onError: (err: any) => {
      setError(parseApiError(err, t('submit.error_component')));
    },
  });

  const datasheetMutation = useMutation({
    mutationFn: async () => {
      if (!dsFile || !submittedItem) throw new Error('No file');
      const formData = new FormData();
      formData.append('file', dsFile);
      formData.append('title', dsTitle || dsFile.name.replace(/\.[^/.]+$/, ''));
      formData.append('source_type', dsSourceType);
      if (dsSourceUrl) formData.append('source_url', dsSourceUrl);
      return componentsApi.uploadDatasheet(submittedItem.id, formData);
    },
    onSuccess: () => {
      setDsFile(null);
      setDsTitle('');
      setDsSourceUrl('');
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <AlertCircle className="h-16 w-16 text-cyber-pink mb-4" />
        <h2 className="font-display text-2xl text-white mb-2">{t('submit.auth_required_title')}</h2>
        <p className="text-gray-400 mb-6 text-center">
          {t('submit.auth_required_desc')}
        </p>
        <a href="/login" className="btn-cyber">
          {t('submit.login_to_continue')}
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

  const handleSubmitAnother = () => {
    setSubmittedItem(null);
    setStep(1);
    setError(null);
    setUploadsDone(false);
    setUploadTab('photos');
    setDsFile(null);
    setDsTitle('');
    setDsSourceUrl('');
    setProductData({ manufacturer: '', model_number: '', revision: '', region: 'global', category: '', year_manufactured: '', fcc_id: '', description: '', teardown_notes: '' });
    setComponentData({ part_number: '', manufacturer: '', component_type: '', package_type: '', description: '', typical_function: '', datasheet_url: '' });
  };

  const viewLink = submittedItem
    ? submittedItem.type === 'product'
      ? `/products/${submittedItem.id}`
      : `/components/${submittedItem.id}/products`
    : '';

  if (submittedItem && !uploadsDone) {
    const dsInputRef = { current: null as HTMLInputElement | null };

    const handleDsFileSelect = () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.pdf,.png,.jpg,.jpeg,.zip';
      input.onchange = (e) => {
        const f = (e.target as HTMLInputElement).files?.[0];
        if (f) setDsFile(f);
      };
      input.click();
    };

    return (
      <div className="py-8">
        <div className="mx-auto max-w-3xl px-4">
          <div className="mb-8 text-center">
            <h1 className="font-display text-3xl font-bold text-white mb-2">
              SUBMIT <span className="text-cyber-green">DOCUMENTATION</span>
            </h1>
            <p className="text-gray-400">{t('submit.step4_subtitle')}</p>
          </div>

          <div className="card-cyber p-6">
            <div className="mb-6">
              <h2 className="font-display text-lg text-white mb-1">
                {t('submit.add_files_title')}
                <span className="text-gray-500 text-sm font-sans font-normal ml-3">{t('submit.add_files_optional')}</span>
              </h2>
              <p className="text-sm text-gray-400">
                {t('submit.add_files_desc', { label: submittedItem.label, type: submittedItem.type })}
              </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-0 mb-6 border-b border-cyber-light/30">
              <button
                onClick={() => setUploadTab('photos')}
                className={clsx(
                  'px-4 py-2 font-mono text-sm border-b-2 -mb-px transition-colors flex items-center gap-2',
                  uploadTab === 'photos'
                    ? 'border-cyber-cyan text-cyber-cyan'
                    : 'border-transparent text-gray-500 hover:text-white'
                )}
              >
                <Camera className="h-4 w-4" />
                {t('submit.photos')}
              </button>
              <button
                onClick={() => setUploadTab('docs')}
                className={clsx(
                  'px-4 py-2 font-mono text-sm border-b-2 -mb-px transition-colors flex items-center gap-2',
                  uploadTab === 'docs'
                    ? 'border-cyber-green text-cyber-green'
                    : 'border-transparent text-gray-500 hover:text-white'
                )}
              >
                <FileText className="h-4 w-4" />
                {submitType === 'product' ? t('submit.documentation') : t('submit.datasheets_tab')}
              </button>
            </div>

            {/* Photos tab */}
            {uploadTab === 'photos' && submitType === 'product' && (
              <ImageUpload productId={submittedItem.id} />
            )}
            {uploadTab === 'photos' && submitType === 'component' && (
              <ImageUpload
                uploadFn={(formData) => componentsApi.uploadImage(submittedItem.id, formData)}
                invalidateKey={['component', submittedItem.id]}
                imageTypes={COMPONENT_IMAGE_TYPES}
                defaultImageType="package"
              />
            )}

            {/* Documentation tab - product */}
            {uploadTab === 'docs' && submitType === 'product' && (
              <SchematicUpload productId={submittedItem.id} />
            )}

            {/* Datasheets tab - component */}
            {uploadTab === 'docs' && submitType === 'component' && (
              <div className="space-y-4">
                {!dsFile ? (
                  <div
                    onClick={handleDsFileSelect}
                    className="border-2 border-dashed border-cyber-light/50 hover:border-cyber-green/50 hover:bg-cyber-dark/50 p-8 text-center cursor-pointer transition-all"
                  >
                    <FileText className="h-10 w-10 mx-auto mb-3 text-gray-500" />
                    <p className="text-gray-400 mb-1">
                      <span className="text-cyber-green">{t('submit.ds_click_upload')}</span>
                    </p>
                    <p className="text-xs text-gray-600 font-mono">{t('submit.ds_accept')}</p>
                  </div>
                ) : (
                  <div className="card-cyber p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-cyber-green/20 border border-cyber-green/30 flex items-center justify-center">
                          <FileText className="h-5 w-5 text-cyber-green" />
                        </div>
                        <div>
                          <div className="text-sm font-mono text-white truncate max-w-xs">{dsFile.name}</div>
                          <div className="text-xs text-gray-500">{(dsFile.size / 1024 / 1024).toFixed(2)} MB</div>
                        </div>
                      </div>
                      <button onClick={() => setDsFile(null)} className="text-cyber-pink hover:text-white transition-colors p-1">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-gray-500 mb-1">{t('submit.ds_title_label')}</label>
                      <input
                        type="text"
                        value={dsTitle}
                        onChange={(e) => setDsTitle(e.target.value)}
                        placeholder={dsFile.name.replace(/\.[^/.]+$/, '')}
                        className="input-cyber w-full"
                      />
                    </div>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-mono text-gray-500 mb-1">{t('submit.ds_source_label')}</label>
                        <select value={dsSourceType} onChange={(e) => setDsSourceType(e.target.value)} className="input-cyber w-full">
                          <option value="official">{t('schematics.upload.source_official')}</option>
                          <option value="community">{t('schematics.upload.source_community')}</option>
                          <option value="reverse_engineered">{t('schematics.upload.source_reverse')}</option>
                          <option value="fcc_filing">{t('schematics.upload.source_fcc')}</option>
                          <option value="leaked">{t('schematics.upload.source_leaked')}</option>
                          <option value="unknown">{t('schematics.upload.source_unknown')}</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-mono text-gray-500 mb-1">{t('submit.ds_source_url_label')}</label>
                        <input
                          type="url"
                          value={dsSourceUrl}
                          onChange={(e) => setDsSourceUrl(e.target.value)}
                          placeholder="https://..."
                          className="input-cyber w-full"
                        />
                      </div>
                    </div>
                    <div className="flex justify-end">
                      <button
                        onClick={() => datasheetMutation.mutate()}
                        disabled={datasheetMutation.isPending}
                        className={clsx(
                          'btn-cyber btn-cyber-green flex items-center gap-2',
                          datasheetMutation.isPending && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {datasheetMutation.isPending ? (
                          <><Loader2 className="h-4 w-4 animate-spin" /> {t('submit.ds_uploading')}</>
                        ) : (
                          <><Upload className="h-4 w-4" /> {t('submit.ds_upload_btn')}</>
                        )}
                      </button>
                    </div>
                  </div>
                )}
                {datasheetMutation.isSuccess && !dsFile && (
                  <div className="flex items-center gap-2 p-3 border border-cyber-green/50 bg-cyber-green/10 text-cyber-green text-sm font-mono">
                    <Check className="h-4 w-4" />
                    {t('submit.ds_success')}
                  </div>
                )}
                {datasheetMutation.isError && (
                  <div className="flex items-center gap-2 p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm font-mono">
                    <AlertCircle className="h-4 w-4" />
                    {t('submit.ds_error')}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Skip / Done */}
          <div className="flex justify-end gap-4 mt-6">
            <button
              onClick={() => setUploadsDone(true)}
              className="text-gray-400 hover:text-white transition-colors font-mono text-sm"
            >
              {t('submit.skip')}
            </button>
            <button
              onClick={() => setUploadsDone(true)}
              className="btn-cyber flex items-center gap-2"
            >
              <Check className="h-4 w-4" />
              {t('submit.done')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (submittedItem && uploadsDone) {
    return (
      <div className="py-8">
        <div className="mx-auto max-w-3xl px-4">
          <div className="mb-8 text-center">
            <h1 className="font-display text-3xl font-bold text-white mb-2">
              SUBMIT <span className="text-cyber-green">DOCUMENTATION</span>
            </h1>
          </div>
          <ModerationNotice
            itemLabel={submittedItem.label}
            viewLink={viewLink}
            onSubmitAnother={handleSubmitAnother}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-3xl px-4">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            SUBMIT <span className="text-cyber-green">DOCUMENTATION</span>
          </h1>
          <p className="text-gray-400">
            {t('submit.subtitle')}
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
            <span className="font-display font-bold">{t('submit.tab_product')}</span>
            <span className="text-xs text-gray-500">{t('submit.tab_product_desc')}</span>
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
            <span className="font-display font-bold">{t('submit.tab_component')}</span>
            <span className="text-xs text-gray-500">{t('submit.tab_component_desc')}</span>
          </button>
        </div>

        {/* PCBTracer hint — product only */}
        {submitType === 'product' && (
          <div className="mb-6 px-4 py-3 border border-cyber-green/30 bg-cyber-green/5 flex items-center justify-between gap-3 text-sm">
            <span className="text-gray-400">
              {t('submit.pcbtracer_hint')}
            </span>
            <a
              href="https://pcbtracer.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 flex items-center gap-1 text-xs font-mono text-cyber-green hover:text-white transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              {t('submit.pcbtracer_link')}
            </a>
          </div>
        )}

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
                  {t('submit.step_basic')}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      {t('submit.manufacturer')} *
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
                      {t('submit.model_number')} *
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
                      {t('submit.category')} *
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
                      {t('submit.region')}
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
                  {t('submit.step_additional')}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      {t('submit.revision')}
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
                      {t('submit.year')}
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
                      {t('submit.fcc_id')}
                    </label>
                    <input
                      type="text"
                      value={productData.fcc_id}
                      onChange={(e) => handleProductChange('fcc_id', e.target.value)}
                      placeholder="e.g., MSQ-RTAX88U"
                      className="input-cyber"
                    />
                    <p className="text-xs text-gray-600 mt-1">
                      {t('submit.fcc_hint')}
                    </p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-mono text-gray-400 mb-2">
                    {t('submit.description')}
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
                  {t('submit.step_review')}
                </h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">{t('submit.review_manufacturer')}</span>
                      <p className="text-white font-mono">{productData.manufacturer}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">{t('submit.review_model')}</span>
                      <p className="text-white font-mono">{productData.model_number}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">{t('submit.review_category')}</span>
                      <p className="text-white font-mono">
                        {CATEGORIES.find((c) => c.value === productData.category)?.label}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">{t('submit.review_region')}</span>
                      <p className="text-white font-mono">
                        {REGIONS.find((r) => r.value === productData.region)?.label}
                      </p>
                    </div>
                    {productData.revision && (
                      <div>
                        <span className="text-gray-500">{t('submit.review_revision')}</span>
                        <p className="text-white font-mono">{productData.revision}</p>
                      </div>
                    )}
                    {productData.fcc_id && (
                      <div>
                        <span className="text-gray-500">{t('submit.review_fcc_id')}</span>
                        <p className="text-white font-mono">{productData.fcc_id}</p>
                      </div>
                    )}
                  </div>
                  {productData.description && (
                    <div>
                      <span className="text-gray-500 text-sm">{t('submit.review_description')}</span>
                      <p className="text-gray-300 text-sm mt-1">{productData.description}</p>
                    </div>
                  )}
                </div>
                <div className="border-t border-cyber-light/30 pt-4">
                  <p className="text-xs text-gray-500">
                    {t('submit.after_submission')}
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
                  {t('submit.back')}
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
                  {t('submit.next')}
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmitProduct}
                  disabled={productMutation.isPending}
                  className="btn-cyber flex items-center gap-2"
                >
                  {productMutation.isPending ? (
                    t('submit.submitting')
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      {t('submit.submit_product')}
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
                  {t('submit.step_identification')}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-mono text-gray-400 mb-2">
                      {t('submit.manufacturer')} *
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
                      {t('submit.part_number')} *
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
                      {t('submit.component_type')} *
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
                      {t('submit.package_type')}
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
                  {t('submit.step_additional')}
                </h2>
                <div>
                  <label className="block text-sm font-mono text-gray-400 mb-2">
                    {t('submit.typical_function')}
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
                    {t('submit.datasheet_url')}
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
                    {t('submit.description')}
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
                  {t('submit.step_review')}
                </h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">{t('submit.review_manufacturer')}</span>
                      <p className="text-white font-mono">{componentData.manufacturer}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">{t('submit.review_part_number')}</span>
                      <p className="text-white font-mono">{componentData.part_number}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">{t('submit.review_type')}</span>
                      <p className="text-white font-mono">
                        {COMPONENT_TYPES.find((ct) => ct.value === componentData.component_type)?.label}
                      </p>
                    </div>
                    {componentData.package_type && (
                      <div>
                        <span className="text-gray-500">{t('submit.review_package')}</span>
                        <p className="text-white font-mono">{componentData.package_type}</p>
                      </div>
                    )}
                  </div>
                  {componentData.typical_function && (
                    <div>
                      <span className="text-gray-500 text-sm">{t('submit.review_function')}</span>
                      <p className="text-gray-300 text-sm mt-1">{componentData.typical_function}</p>
                    </div>
                  )}
                  {componentData.description && (
                    <div>
                      <span className="text-gray-500 text-sm">{t('submit.review_description')}</span>
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
                  {t('submit.back')}
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
                  {t('submit.next')}
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmitComponent}
                  disabled={componentMutation.isPending}
                  className="btn-cyber flex items-center gap-2"
                >
                  {componentMutation.isPending ? (
                    t('submit.submitting')
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      {t('submit.submit_component')}
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Info box */}
        <div className="mt-8 p-4 border border-cyber-light/20 bg-cyber-dark/50">
          <h3 className="font-mono text-sm text-cyber-cyan mb-2">{t('submit.guidelines_title')}</h3>
          <ul className="text-xs text-gray-500 space-y-1">
            <li>• {t('submit.guideline_accuracy')}</li>
            <li>• {t('submit.guideline_fcc')}</li>
            <li>• {t('submit.guideline_photos')}</li>
            <li>• {t('submit.guideline_review')}</li>
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
