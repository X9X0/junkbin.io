import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { components } from '../api/endpoints';
import { Cpu, Grid, List, Search, ChevronDown, ExternalLink, CheckCircle, Package } from 'lucide-react';
import clsx from 'clsx';
import Pagination from '../components/Pagination';
import { ComponentGridSkeleton } from '../components/Skeleton';

const COMPONENT_TYPES = [
  { value: '', label: 'All Types' },
  // Active
  { value: 'ic', label: 'Integrated Circuit' },
  { value: 'mcu', label: 'Microcontroller' },
  { value: 'transistor', label: 'Transistor' },
  { value: 'mosfet', label: 'MOSFET' },
  { value: 'diode', label: 'Diode' },
  { value: 'regulator', label: 'Voltage Regulator' },
  { value: 'opamp', label: 'Op-Amp' },
  // Passive
  { value: 'resistor', label: 'Resistor' },
  { value: 'capacitor', label: 'Capacitor' },
  { value: 'inductor', label: 'Inductor' },
  { value: 'transformer', label: 'Transformer' },
  { value: 'crystal', label: 'Crystal/Oscillator' },
  { value: 'fuse', label: 'Fuse' },
  { value: 'ferrite', label: 'Ferrite Bead' },
  // Electromechanical
  { value: 'relay', label: 'Relay' },
  { value: 'switch', label: 'Switch' },
  { value: 'connector', label: 'Connector' },
  { value: 'socket', label: 'Socket/Header' },
  // RF/Wireless
  { value: 'antenna', label: 'Antenna' },
  { value: 'rf_module', label: 'RF Module' },
  { value: 'balun', label: 'Balun/Filter' },
  // Power
  { value: 'battery', label: 'Battery/Cell' },
  { value: 'power_jack', label: 'Power Jack' },
  { value: 'usb_port', label: 'USB Port' },
  // Display/Output
  { value: 'led', label: 'LED' },
  { value: 'display', label: 'Display/LCD' },
  { value: 'speaker', label: 'Speaker/Buzzer' },
  // Sensors
  { value: 'sensor', label: 'Sensor' },
  { value: 'thermistor', label: 'Thermistor/NTC' },
  // Modules
  { value: 'module', label: 'Module/Daughter Board' },
  { value: 'pcb_assembly', label: 'PCB Assembly' },
  // Cabling
  { value: 'cable', label: 'Cable/Wire Harness' },
  { value: 'flex_cable', label: 'Flex Cable/FPC' },
  { value: 'coax', label: 'Coaxial Cable' },
  // Other
  { value: 'heatsink', label: 'Heatsink' },
  { value: 'shield', label: 'EMI Shield' },
  { value: 'mechanical', label: 'Mechanical Part' },
  { value: 'other', label: 'Other' },
];

export default function Components() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const search = searchParams.get('search') || '';
  const componentType = searchParams.get('component_type') || '';
  const ordering = searchParams.get('ordering') || '-usage_count';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading } = useQuery({
    queryKey: ['components', { search, component_type: componentType, ordering, page }],
    queryFn: () => components.list({ search, component_type: componentType, ordering, page }),
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
      <div className="mx-auto max-w-7xl px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            {t('components.title')} <span className="text-cyber-pink">{t('components.title_highlight')}</span>
          </h1>
          <p className="text-gray-400">
            {t('components.subtitle')}
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
                placeholder={t('components.search_placeholder')}
                className="input-cyber pl-10"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
            </div>

            {/* Component Type */}
            <div className="relative">
              <select
                value={componentType}
                onChange={(e) => updateFilter('component_type', e.target.value)}
                className="input-cyber appearance-none pr-10 w-full lg:w-56"
              >
                {COMPONENT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.value === '' ? t('components.all_types') : type.label}
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
                <option value="-usage_count">{t('components.most_used')}</option>
                <option value="usage_count">{t('components.least_used')}</option>
                <option value="manufacturer">{t('components.manufacturer_az')}</option>
                <option value="part_number">{t('components.part_number_az')}</option>
                <option value="-created_at">{t('components.newest_first')}</option>
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
                    ? 'border-cyber-pink text-cyber-pink bg-cyber-pink/10'
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
                    ? 'border-cyber-pink text-cyber-pink bg-cyber-pink/10'
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
            {t('components.count_found', { count: data.count })}
          </div>
        )}

        {/* Loading state */}
        {isLoading && <ComponentGridSkeleton count={8} />}

        {/* Components Grid */}
        {data && !isLoading && (
          <div
            className={clsx(
              viewMode === 'grid'
                ? 'grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                : 'flex flex-col gap-4'
            )}
          >
            {data.results.map((component) => (
              <Link
                key={component.id}
                to={`/components/${component.id}/products`}
                className={clsx(
                  'card-cyber hover:border-cyber-pink/50 transition-all group block',
                  viewMode === 'grid' ? 'p-4' : 'p-4 flex gap-4'
                )}
              >
                {/* Image / Icon */}
                <div
                  className={clsx(
                    'bg-cyber-black flex items-center justify-center border border-cyber-light/20 overflow-hidden',
                    viewMode === 'grid' ? 'aspect-square mb-4' : 'w-16 h-16 flex-shrink-0'
                  )}
                >
                  {component.primary_image ? (
                    <img
                      src={component.primary_image.thumbnail || component.primary_image.image}
                      alt={component.part_number}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <Package className="h-8 w-8 text-cyber-pink/60" />
                  )}
                </div>

                {/* Info */}
                <div className={viewMode === 'list' ? 'flex-1 min-w-0' : ''}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-cyber-pink">
                      {component.manufacturer}
                    </span>
                    {component.is_verified && (
                      <span title={t('components.verified')}>
                        <CheckCircle className="h-3.5 w-3.5 text-cyber-green" />
                      </span>
                    )}
                  </div>

                  <h3 className="font-mono font-semibold text-white group-hover:text-cyber-pink transition-colors truncate">
                    {component.part_number}
                  </h3>

                  <div className="text-xs text-gray-500 mt-1">
                    {component.component_type_display || component.component_type}
                    {component.package_type && (
                      <span className="ml-2 text-gray-600">• {component.package_type}</span>
                    )}
                  </div>

                  {component.primary_value && (
                    <div className="font-mono text-sm text-cyber-yellow mt-1">
                      {component.primary_value}
                    </div>
                  )}

                  {component.description && viewMode === 'list' && (
                    <p className="mt-2 text-sm text-gray-400 line-clamp-2">
                      {component.description}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 text-xs">
                    <span className="text-cyber-cyan">
                      {t('components.found_in_products', { count: component.usage_count })}
                    </span>
                    {component.datasheet_url && (
                      <button
                        className="flex items-center gap-1 text-gray-500 hover:text-cyber-cyan transition-colors"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          window.open(component.datasheet_url, '_blank', 'noopener,noreferrer');
                        }}
                      >
                        <ExternalLink className="h-3 w-3" />
                        {t('components.datasheet')}
                      </button>
                    )}
                  </div>

                  {/* Cross-reference link */}
                  <div className="mt-3 pt-3 border-t border-cyber-light/20">
                    <span
                      className="text-xs font-mono text-cyber-cyan group-hover:text-white transition-colors flex items-center gap-1"
                    >
                      <Cpu className="h-3.5 w-3.5" />
                      {t('components.find_products')}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Empty state */}
        {data && data.results.length === 0 && (
          <div className="text-center py-20">
            <Package className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="font-display text-xl text-white mb-2">{t('components.no_components_title')}</h3>
            <p className="text-gray-500 mb-6">
              {t('components.no_components_desc')}
            </p>
            <Link to="/submit" className="btn-cyber">
              {t('components.add_component')}
            </Link>
          </div>
        )}

        {/* Pagination */}
        {data && totalPages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={goToPage}
            color="pink"
            className="mt-8"
          />
        )}
      </div>
    </div>
  );
}
