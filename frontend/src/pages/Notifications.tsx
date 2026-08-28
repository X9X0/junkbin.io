import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, Bell } from 'lucide-react';
import { notifications } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import Pagination from '../components/Pagination';
import type { AppNotification } from '../types';

const PAGE_SIZE = 20;

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

export default function Notifications() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading } = useQuery({
    queryKey: ['notificationList', 'full', page],
    queryFn: () => notifications.list({ page, page_size: PAGE_SIZE }),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 0;

  const goToPage = (p: number) => {
    const params = new URLSearchParams(searchParams);
    if (p > 1) params.set('page', String(p));
    else params.delete('page');
    setSearchParams(params);
  };

  const markRead = async (n: AppNotification) => {
    if (n.is_read) return;
    await notifications.markRead(n.id);
    queryClient.invalidateQueries({ queryKey: ['notificationList'] });
    queryClient.invalidateQueries({ queryKey: ['notificationCount'] });
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-mono text-cyber-cyan flex items-center gap-2 mb-6">
        <Bell className="h-6 w-6" />
        {t('notifications.title', 'Notifications')}
      </h1>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-cyber-cyan" />
        </div>
      ) : !data?.results.length ? (
        <div className="text-center py-12 text-gray-500 font-mono">
          {t('notifications.empty', "You don't have any notifications yet.")}
        </div>
      ) : (
        <div className="border border-cyber-light/20">
          {data.results.map((n) => (
            <Link
              key={n.id}
              to={n.url || '#'}
              onClick={() => markRead(n)}
              className={`block px-4 py-3 border-b border-cyber-light/10 last:border-b-0 hover:bg-cyber-light/10 transition-colors ${
                n.is_read ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-sm text-gray-200 font-mono">{n.title}</div>
                  {n.body && <div className="text-sm text-gray-500 mt-1">{n.body}</div>}
                </div>
                <div className="text-xs text-gray-600 whitespace-nowrap font-mono">
                  {formatDateTime(n.created_at)}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={goToPage}
          color="cyan"
          className="mt-8"
        />
      )}
    </div>
  );
}
