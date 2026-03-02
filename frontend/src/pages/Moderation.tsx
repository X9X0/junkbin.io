import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, AlertTriangle, Clock, CheckCircle, Eye, Users, Package, FileText, Wrench, ImageIcon, BookOpen, Check, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { reports, reviews, products, schematics, recipes, productImages, componentImages, componentDatasheets } from '../api/endpoints';
import type { Report, UserReview, Product, ProductImage, Schematic, Recipe, ComponentDatasheet, ComponentImage } from '../types';
import Pagination from '../components/Pagination';
import ResolveReportModal from '../components/moderation/ResolveReportModal';
import UserReviewPanel from '../components/moderation/UserReviewPanel';
import clsx from 'clsx';

const reportStatusColors: Record<string, string> = {
  pending: 'border-cyber-yellow/50 text-cyber-yellow',
  investigating: 'border-cyber-cyan/50 text-cyber-cyan',
  resolved_valid: 'border-cyber-green/50 text-cyber-green',
  resolved_invalid: 'border-cyber-pink/50 text-cyber-pink',
  dismissed: 'border-gray-600 text-gray-500',
};

const reviewStatusColors: Record<string, string> = {
  pending: 'border-cyber-yellow/50 text-cyber-yellow',
  in_progress: 'border-cyber-cyan/50 text-cyber-cyan',
  cleared: 'border-cyber-green/50 text-cyber-green',
  warning_issued: 'border-cyber-yellow/50 text-cyber-yellow',
  restricted: 'border-orange-400/50 text-orange-400',
  suspended: 'border-red-500/50 text-red-500',
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Moderation() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);

  const tab = searchParams.get('tab') || 'pending';
  const status = searchParams.get('status') || '';
  const reason = searchParams.get('reason') || '';
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Access control
  if (!user?.is_moderator && !user?.is_staff) {
    return (
      <div className="py-20 text-center">
        <Shield className="h-16 w-16 text-gray-600 mx-auto mb-4" />
        <h2 className="font-display text-2xl text-white mb-2">{t('moderation.access_denied')}</h2>
        <p className="text-gray-500">{t('moderation.access_denied_desc')}</p>
      </div>
    );
  }

  const updateFilter = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    if (key !== 'page') newParams.delete('page');
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
            MODERATION <span className="text-cyber-yellow">DASHBOARD</span>
          </h1>
          <p className="text-gray-400 font-mono text-sm">Review reports and manage user reviews</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-cyber-light/30">
          <button
            onClick={() => updateFilter('tab', 'pending')}
            className={clsx(
              'px-4 py-3 font-mono text-sm border-b-2 transition-colors flex items-center gap-2',
              tab === 'pending'
                ? 'border-cyber-yellow text-cyber-yellow'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            )}
          >
            <Package className="h-4 w-4" />
            {t('moderation.tab_pending')}
          </button>
          <button
            onClick={() => updateFilter('tab', 'reviews')}
            className={clsx(
              'px-4 py-3 font-mono text-sm border-b-2 transition-colors flex items-center gap-2',
              tab === 'reviews'
                ? 'border-cyber-yellow text-cyber-yellow'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            )}
          >
            <Users className="h-4 w-4" />
            {t('moderation.tab_reviews')}
          </button>
          <button
            onClick={() => updateFilter('tab', 'reports')}
            className={clsx(
              'px-4 py-3 font-mono text-sm border-b-2 transition-colors flex items-center gap-2',
              tab === 'reports'
                ? 'border-cyber-yellow text-cyber-yellow'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            )}
          >
            <AlertTriangle className="h-4 w-4" />
            {t('moderation.tab_reports')}
          </button>
        </div>

        {tab === 'pending' ? (
          <PendingContentTab />
        ) : tab === 'reviews' ? (
          <ReviewsTab
            status={status}
            page={page}
            updateFilter={updateFilter}
            goToPage={goToPage}
            onReview={setSelectedReviewId}
          />
        ) : tab === 'reports' ? (
          <ReportsTab
            status={status}
            reason={reason}
            page={page}
            updateFilter={updateFilter}
            goToPage={goToPage}
            onReview={setSelectedReport}
          />
        ) : null}
      </div>

      {/* Modals */}
      {selectedReport && (
        <ResolveReportModal
          isOpen={true}
          onClose={() => setSelectedReport(null)}
          report={selectedReport}
        />
      )}
      {selectedReviewId && (
        <UserReviewPanel
          isOpen={true}
          onClose={() => setSelectedReviewId(null)}
          reviewId={selectedReviewId}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Reports Tab                                                        */
/* ------------------------------------------------------------------ */

interface ReportsTabProps {
  status: string;
  reason: string;
  page: number;
  updateFilter: (key: string, value: string) => void;
  goToPage: (page: number) => void;
  onReview: (report: Report) => void;
}

function ReportsTab({ status, reason, page, updateFilter, goToPage, onReview }: ReportsTabProps) {
  const { t } = useTranslation();
  const pageSize = 20;

  const { data: statsData } = useQuery({
    queryKey: ['reportStats'],
    queryFn: reports.stats,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['reports', { status, reason, page }],
    queryFn: () => reports.list({ status: status || undefined, reason: reason || undefined, page }),
  });

  const totalPages = data ? Math.ceil(data.count / pageSize) : 0;

  return (
    <>
      {/* Stats bar */}
      {statsData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <StatCard label={t('moderation.status_pending')} value={statsData.pending} color="text-cyber-yellow" icon={Clock} />
          <StatCard label="TOTAL" value={statsData.total} color="text-gray-400" icon={AlertTriangle} />
          <StatCard label="VALID" value={statsData.resolved_valid} color="text-cyber-green" icon={CheckCircle} />
          <StatCard label="INVALID" value={statsData.resolved_invalid} color="text-cyber-pink" icon={AlertTriangle} />
        </div>
      )}

      {/* Filters */}
      <div className="card-cyber p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <select
            value={status}
            onChange={(e) => updateFilter('status', e.target.value)}
            className="input-cyber appearance-none"
          >
            <option value="">{t('moderation.all_statuses')}</option>
            <option value="pending">{t('moderation.status_pending')}</option>
            <option value="investigating">{t('moderation.status_investigating')}</option>
            <option value="resolved_valid">{t('moderation.status_resolved_valid')}</option>
            <option value="resolved_invalid">{t('moderation.status_resolved_invalid')}</option>
            <option value="dismissed">{t('moderation.status_dismissed')}</option>
          </select>
          <select
            value={reason}
            onChange={(e) => updateFilter('reason', e.target.value)}
            className="input-cyber appearance-none"
          >
            <option value="">{t('moderation.all_reasons')}</option>
            <option value="incorrect_info">{t('moderation.reason_incorrect')}</option>
            <option value="duplicate">{t('moderation.reason_duplicate')}</option>
            <option value="spam">{t('moderation.reason_spam')}</option>
            <option value="inappropriate">{t('moderation.reason_inappropriate')}</option>
            <option value="copyright">{t('moderation.reason_copyright')}</option>
            <option value="other">{t('moderation.reason_other')}</option>
          </select>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading reports...</div>
      ) : data && data.results.length > 0 ? (
        <>
          <div className="text-sm text-gray-500 font-mono mb-4">{t('moderation.count_reports', { count: data.count })}</div>

          {/* Table */}
          <div className="overflow-x-auto card-cyber">
            <table className="w-full">
              <thead>
                <tr className="border-b border-cyber-light/30">
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_reporter')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_reported')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_reason')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500 hidden md:table-cell">{t('moderation.col_content')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500 hidden lg:table-cell">{t('moderation.col_date')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_status')}</th>
                  <th className="text-right px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_actions')}</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((report: Report) => (
                  <tr key={report.id} className="border-b border-cyber-light/10 hover:bg-cyber-light/5 transition-colors">
                    <td className="px-4 py-3 text-sm text-white">{report.reporter?.username || '?'}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{report.reported_user?.username || 'N/A'}</td>
                    <td className="px-4 py-3 text-sm text-cyber-yellow">{report.reason_display}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 hidden md:table-cell">{report.content_type_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 font-mono hidden lg:table-cell">{formatDate(report.created_at)}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'px-2 py-0.5 text-xs font-mono border',
                        reportStatusColors[report.status] || 'border-gray-600 text-gray-500'
                      )}>
                        {report.status_display}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {['pending', 'investigating'].includes(report.status) ? (
                        <button
                          onClick={() => onReview(report)}
                          className="text-cyber-cyan hover:text-white text-sm font-mono flex items-center gap-1 ml-auto transition-colors"
                        >
                          <Eye className="h-4 w-4" />
                          {t('moderation.btn_review')}
                        </button>
                      ) : (
                        <button
                          onClick={() => onReview(report)}
                          className="text-gray-600 hover:text-gray-400 text-sm font-mono flex items-center gap-1 ml-auto transition-colors"
                        >
                          <Eye className="h-4 w-4" />
                          {t('moderation.btn_view')}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={goToPage}
              color="cyan"
              className="mt-8"
            />
          )}
        </>
      ) : (
        <div className="text-center py-20">
          <CheckCircle className="h-16 w-16 text-cyber-green/30 mx-auto mb-4" />
          <h3 className="font-display text-xl text-white mb-2">{t('moderation.no_reports')}</h3>
          <p className="text-gray-500">No reports match the current filters.</p>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Reviews Tab                                                        */
/* ------------------------------------------------------------------ */

interface ReviewsTabProps {
  status: string;
  page: number;
  updateFilter: (key: string, value: string) => void;
  goToPage: (page: number) => void;
  onReview: (id: string) => void;
}

function ReviewsTab({ status, page, updateFilter, goToPage, onReview }: ReviewsTabProps) {
  const { t } = useTranslation();
  const pageSize = 20;

  const { data, isLoading } = useQuery({
    queryKey: ['userReviews', { status, page }],
    queryFn: () => reviews.list({ status: status || undefined, page }),
  });

  const totalPages = data ? Math.ceil(data.count / pageSize) : 0;

  return (
    <>
      {/* Filters */}
      <div className="card-cyber p-4 mb-6">
        <select
          value={status}
          onChange={(e) => updateFilter('status', e.target.value)}
          className="input-cyber appearance-none"
        >
          <option value="">{t('moderation.all_statuses')}</option>
          <option value="pending">{t('moderation.status_pending')}</option>
          <option value="in_progress">In Progress</option>
          <option value="cleared">Cleared</option>
          <option value="warning_issued">Warning Issued</option>
          <option value="restricted">Restricted</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading user reviews...</div>
      ) : data && data.results.length > 0 ? (
        <>
          <div className="text-sm text-gray-500 font-mono mb-4">{data.count} reviews found</div>

          <div className="overflow-x-auto card-cyber">
            <table className="w-full">
              <thead>
                <tr className="border-b border-cyber-light/30">
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_user')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_type')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_strikes')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500 hidden md:table-cell">{t('moderation.col_created')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_status')}</th>
                  <th className="text-right px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_actions')}</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((review: UserReview) => (
                  <tr key={review.id} className="border-b border-cyber-light/10 hover:bg-cyber-light/5 transition-colors">
                    <td className="px-4 py-3 text-sm text-white">{review.user.username}</td>
                    <td className="px-4 py-3 text-sm text-gray-400">{review.review_type_display}</td>
                    <td className="px-4 py-3 text-sm text-cyber-pink font-mono">{review.trigger_report_count}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 font-mono hidden md:table-cell">{formatDate(review.created_at)}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'px-2 py-0.5 text-xs font-mono border',
                        reviewStatusColors[review.status] || 'border-gray-600 text-gray-500'
                      )}>
                        {review.status_display}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => onReview(review.id)}
                        className="text-cyber-cyan hover:text-white text-sm font-mono flex items-center gap-1 ml-auto transition-colors"
                      >
                        <Eye className="h-4 w-4" />
                        {['pending', 'in_progress'].includes(review.status) ? t('moderation.btn_review') : t('moderation.btn_view')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={goToPage}
              color="cyan"
              className="mt-8"
            />
          )}
        </>
      ) : (
        <div className="text-center py-20">
          <Shield className="h-16 w-16 text-cyber-green/30 mx-auto mb-4" />
          <h3 className="font-display text-xl text-white mb-2">{t('moderation.no_reviews')}</h3>
          <p className="text-gray-500">No user reviews match the current filters.</p>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Pending Content Tab                                                */
/* ------------------------------------------------------------------ */

type ContentFilter = 'all' | 'products' | 'schematics' | 'recipes' | 'images' | 'component_images' | 'datasheets';

type PendingItem =
  | { type: 'product'; data: Product }
  | { type: 'schematic'; data: Schematic }
  | { type: 'recipe'; data: Recipe }
  | { type: 'image'; data: ProductImage }
  | { type: 'component_image'; data: ComponentImage & { component: string; uploaded_at: string } }
  | { type: 'datasheet'; data: ComponentDatasheet };

const typeBadgeColors: Record<string, string> = {
  product: 'border-cyber-cyan/50 text-cyber-cyan',
  schematic: 'border-cyber-yellow/50 text-cyber-yellow',
  recipe: 'border-cyber-green/50 text-cyber-green',
  image: 'border-cyber-pink/50 text-cyber-pink',
  component_image: 'border-orange-400/50 text-orange-400',
  datasheet: 'border-purple-400/50 text-purple-400',
};

const typeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  product: Package,
  schematic: FileText,
  recipe: Wrench,
  image: ImageIcon,
  component_image: ImageIcon,
  datasheet: BookOpen,
};

function PendingContentTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [contentFilter, setContentFilter] = useState<ContentFilter>('all');

  const { data: counts } = useQuery({
    queryKey: ['pendingCounts'],
    queryFn: products.pendingCounts,
  });

  const { data: pendingProducts, isLoading: loadingProducts } = useQuery({
    queryKey: ['pendingProducts'],
    queryFn: () => products.list({ is_approved: 'false' as any, page_size: 100 }),
    enabled: contentFilter === 'all' || contentFilter === 'products',
  });

  const { data: pendingSchematics, isLoading: loadingSchematics } = useQuery({
    queryKey: ['pendingSchematics'],
    queryFn: () => schematics.list({ is_approved: 'false', page_size: 100 }),
    enabled: contentFilter === 'all' || contentFilter === 'schematics',
  });

  const { data: pendingRecipes, isLoading: loadingRecipes } = useQuery({
    queryKey: ['pendingRecipes'],
    queryFn: () => recipes.list({ is_approved: 'false', page_size: 100 }),
    enabled: contentFilter === 'all' || contentFilter === 'recipes',
  });

  const { data: pendingImages, isLoading: loadingImages } = useQuery({
    queryKey: ['pendingImages'],
    queryFn: () => productImages.list({ is_approved: 'false', page_size: 100 }),
    enabled: contentFilter === 'all' || contentFilter === 'images',
  });

  const { data: pendingComponentImages, isLoading: loadingComponentImages } = useQuery({
    queryKey: ['pendingComponentImages'],
    queryFn: () => componentImages.list({ is_approved: 'false', page_size: 100 }),
    enabled: contentFilter === 'all' || contentFilter === 'component_images',
  });

  const { data: pendingDatasheets, isLoading: loadingDatasheets } = useQuery({
    queryKey: ['pendingDatasheets'],
    queryFn: () => componentDatasheets.list({ is_approved: 'false', page_size: 100 }),
    enabled: contentFilter === 'all' || contentFilter === 'datasheets',
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['pendingCounts'] });
    queryClient.invalidateQueries({ queryKey: ['pendingProducts'] });
    queryClient.invalidateQueries({ queryKey: ['pendingSchematics'] });
    queryClient.invalidateQueries({ queryKey: ['pendingRecipes'] });
    queryClient.invalidateQueries({ queryKey: ['pendingImages'] });
    queryClient.invalidateQueries({ queryKey: ['pendingComponentImages'] });
    queryClient.invalidateQueries({ queryKey: ['pendingDatasheets'] });
  };

  const approveProduct = useMutation({
    mutationFn: (id: string) => products.approve(id),
    onSuccess: invalidateAll,
  });
  const rejectProduct = useMutation({
    mutationFn: (id: string) => products.reject(id),
    onSuccess: invalidateAll,
  });
  const approveSchematic = useMutation({
    mutationFn: (id: string) => schematics.approve(id),
    onSuccess: invalidateAll,
  });
  const rejectSchematic = useMutation({
    mutationFn: (id: string) => schematics.reject(id),
    onSuccess: invalidateAll,
  });
  const approveRecipe = useMutation({
    mutationFn: (id: string) => recipes.approve(id),
    onSuccess: invalidateAll,
  });
  const rejectRecipe = useMutation({
    mutationFn: (id: string) => recipes.reject(id),
    onSuccess: invalidateAll,
  });
  const approveImage = useMutation({
    mutationFn: (id: string) => productImages.approve(id),
    onSuccess: invalidateAll,
  });
  const rejectImage = useMutation({
    mutationFn: (id: string) => productImages.reject(id),
    onSuccess: invalidateAll,
  });
  const approveComponentImage = useMutation({
    mutationFn: (id: string) => componentImages.approve(id),
    onSuccess: invalidateAll,
  });
  const rejectComponentImage = useMutation({
    mutationFn: (id: string) => componentImages.reject(id),
    onSuccess: invalidateAll,
  });
  const approveDatasheet = useMutation({
    mutationFn: (id: string) => componentDatasheets.approve(id),
    onSuccess: invalidateAll,
  });
  const rejectDatasheet = useMutation({
    mutationFn: (id: string) => componentDatasheets.reject(id),
    onSuccess: invalidateAll,
  });

  // Merge items into a unified list
  const items: PendingItem[] = [];
  if (contentFilter === 'all' || contentFilter === 'products') {
    (pendingProducts?.results || []).forEach((p) => items.push({ type: 'product', data: p }));
  }
  if (contentFilter === 'all' || contentFilter === 'schematics') {
    (pendingSchematics?.results || []).forEach((s) => items.push({ type: 'schematic', data: s }));
  }
  if (contentFilter === 'all' || contentFilter === 'recipes') {
    (pendingRecipes?.results || []).forEach((r) => items.push({ type: 'recipe', data: r }));
  }
  if (contentFilter === 'all' || contentFilter === 'images') {
    (pendingImages?.results || []).forEach((i) => items.push({ type: 'image', data: i }));
  }
  if (contentFilter === 'all' || contentFilter === 'component_images') {
    (pendingComponentImages?.results || []).forEach((i) => items.push({ type: 'component_image', data: i }));
  }
  if (contentFilter === 'all' || contentFilter === 'datasheets') {
    (pendingDatasheets?.results || []).forEach((d) => items.push({ type: 'datasheet', data: d }));
  }

  // Sort by date descending
  items.sort((a, b) => {
    const dateA = 'created_at' in a.data ? a.data.created_at : ((a.data as Schematic | ProductImage).uploaded_at || '');
    const dateB = 'created_at' in b.data ? b.data.created_at : ((b.data as Schematic | ProductImage).uploaded_at || '');
    return new Date(dateB).getTime() - new Date(dateA).getTime();
  });

  const isLoading = loadingProducts || loadingSchematics || loadingRecipes || loadingImages || loadingComponentImages || loadingDatasheets;

  const getItemTitle = (item: PendingItem): string => {
    if (item.type === 'product') return `${item.data.manufacturer} ${item.data.model_number}`;
    if (item.type === 'schematic') return (item.data as Schematic).title;
    if (item.type === 'image') {
      const img = item.data as ProductImage;
      return img.caption || `${img.image_type} image`;
    }
    if (item.type === 'component_image') {
      const img = item.data as ComponentImage;
      return img.caption || `${img.image_type || 'component'} image`;
    }
    if (item.type === 'datasheet') return (item.data as ComponentDatasheet).title;
    return (item.data as Recipe).name;
  };

  const getItemUser = (item: PendingItem): string => {
    if (item.type === 'schematic') return (item.data as Schematic).uploaded_by?.username || 'Unknown';
    if (item.type === 'image') return (item.data as ProductImage).uploaded_by?.username || 'Unknown';
    if (item.type === 'component_image') return (item.data as ComponentImage).uploaded_by?.username || 'Unknown';
    if (item.type === 'datasheet') return (item.data as ComponentDatasheet).uploaded_by?.username || 'Unknown';
    return (item.data as Product | Recipe).created_by?.username || 'Unknown';
  };

  const getItemDate = (item: PendingItem): string => {
    if (item.type === 'schematic') return (item.data as Schematic).uploaded_at;
    if (item.type === 'image') return (item.data as ProductImage).uploaded_at || '';
    if (item.type === 'component_image') return (item.data as any).uploaded_at || '';
    if (item.type === 'datasheet') return (item.data as ComponentDatasheet).uploaded_at;
    return (item.data as Product | Recipe).created_at;
  };

  const getItemLink = (item: PendingItem): string => {
    if (item.type === 'product') return `/products/${item.data.id}`;
    if (item.type === 'recipe') return `/recipes/${item.data.id}`;
    if (item.type === 'image') return `/products/${(item.data as ProductImage).product}`;
    if (item.type === 'component_image') return `/components/${(item.data as any).component}`;
    if (item.type === 'datasheet') return `/components/${(item.data as ComponentDatasheet).component}`;
    return `/products/${(item.data as Schematic).product}`;
  };

  const handleApprove = (item: PendingItem) => {
    if (item.type === 'product') approveProduct.mutate(item.data.id);
    else if (item.type === 'schematic') approveSchematic.mutate(item.data.id);
    else if (item.type === 'image') approveImage.mutate(item.data.id);
    else if (item.type === 'component_image') approveComponentImage.mutate(item.data.id!);
    else if (item.type === 'datasheet') approveDatasheet.mutate(item.data.id);
    else approveRecipe.mutate(item.data.id);
  };

  const handleReject = (item: PendingItem) => {
    if (item.type === 'product') rejectProduct.mutate(item.data.id);
    else if (item.type === 'schematic') rejectSchematic.mutate(item.data.id);
    else if (item.type === 'image') rejectImage.mutate(item.data.id);
    else if (item.type === 'component_image') rejectComponentImage.mutate(item.data.id!);
    else if (item.type === 'datasheet') rejectDatasheet.mutate(item.data.id);
    else rejectRecipe.mutate(item.data.id);
  };

  const isMutating = approveProduct.isPending || rejectProduct.isPending
    || approveSchematic.isPending || rejectSchematic.isPending
    || approveRecipe.isPending || rejectRecipe.isPending
    || approveImage.isPending || rejectImage.isPending
    || approveComponentImage.isPending || rejectComponentImage.isPending
    || approveDatasheet.isPending || rejectDatasheet.isPending;

  return (
    <>
      {/* Stat cards */}
      {counts && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <StatCard label="PRODUCTS" value={counts.products} color="text-cyber-cyan" icon={Package} />
          <StatCard label="SCHEMATICS" value={counts.schematics} color="text-cyber-yellow" icon={FileText} />
          <StatCard label="RECIPES" value={counts.recipes} color="text-cyber-green" icon={Wrench} />
          <StatCard label="IMAGES" value={counts.images} color="text-cyber-pink" icon={ImageIcon} />
          <StatCard label="COMP IMAGES" value={counts.component_images} color="text-orange-400" icon={ImageIcon} />
          <StatCard label="DATASHEETS" value={counts.datasheets} color="text-purple-400" icon={BookOpen} />
        </div>
      )}

      {/* Sub-filter */}
      <div className="card-cyber p-4 mb-6">
        <div className="flex gap-2 flex-wrap">
          {(['all', 'products', 'schematics', 'recipes', 'images', 'component_images', 'datasheets'] as ContentFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setContentFilter(f)}
              className={clsx(
                'px-3 py-1.5 font-mono text-xs border transition-colors',
                contentFilter === f
                  ? 'border-cyber-yellow text-cyber-yellow bg-cyber-yellow/10'
                  : 'border-cyber-light/30 text-gray-500 hover:text-gray-300'
              )}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading pending content...</div>
      ) : items.length > 0 ? (
        <>
          <div className="text-sm text-gray-500 font-mono mb-4">{items.length} pending items</div>

          <div className="overflow-x-auto card-cyber">
            <table className="w-full">
              <thead>
                <tr className="border-b border-cyber-light/30">
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_type')}</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500">TITLE</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500 hidden md:table-cell">SUBMITTED BY</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-gray-500 hidden lg:table-cell">{t('moderation.col_date')}</th>
                  <th className="text-right px-4 py-3 font-mono text-xs text-gray-500">{t('moderation.col_actions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const TypeIcon = typeIcons[item.type];
                  return (
                    <tr key={`${item.type}-${item.data.id}`} className="border-b border-cyber-light/10 hover:bg-cyber-light/5 transition-colors">
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'px-2 py-0.5 text-xs font-mono border inline-flex items-center gap-1',
                          typeBadgeColors[item.type]
                        )}>
                          <TypeIcon className="h-3 w-3" />
                          {item.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <Link to={getItemLink(item)} className="text-white hover:text-cyber-cyan transition-colors">
                          {getItemTitle(item)}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400 hidden md:table-cell">{getItemUser(item)}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 font-mono hidden lg:table-cell">{formatDate(getItemDate(item))}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center gap-2 justify-end">
                          <Link
                            to={getItemLink(item)}
                            className="text-cyber-cyan hover:text-white text-sm font-mono flex items-center gap-1 transition-colors"
                          >
                            <Eye className="h-4 w-4" />
                            {t('moderation.btn_view')}
                          </Link>
                          <button
                            onClick={() => handleApprove(item)}
                            disabled={isMutating}
                            className="text-cyber-green hover:text-white text-sm font-mono flex items-center gap-1 transition-colors disabled:opacity-50"
                          >
                            <Check className="h-4 w-4" />
                            APPROVE
                          </button>
                          <button
                            onClick={() => handleReject(item)}
                            disabled={isMutating}
                            className="text-cyber-pink hover:text-white text-sm font-mono flex items-center gap-1 transition-colors disabled:opacity-50"
                          >
                            <X className="h-4 w-4" />
                            REJECT
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="text-center py-20">
          <CheckCircle className="h-16 w-16 text-cyber-green/30 mx-auto mb-4" />
          <h3 className="font-display text-xl text-white mb-2">{t('moderation.no_reports')}</h3>
          <p className="text-gray-500">No pending content to review.</p>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Stat Card                                                          */
/* ------------------------------------------------------------------ */

function StatCard({ label, value, color, icon: Icon }: {
  label: string;
  value: number;
  color: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="card-cyber p-4 flex items-center gap-3">
      <Icon className={clsx('h-5 w-5', color)} />
      <div>
        <p className={clsx('text-2xl font-display font-bold', color)}>{value}</p>
        <p className="text-xs font-mono text-gray-500">{label}</p>
      </div>
    </div>
  );
}
