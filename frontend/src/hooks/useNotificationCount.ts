import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { notifications } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { usePageVisibility } from './usePageVisibility';

/**
 * Mirrors useUnreadCount.ts's polling pattern for messages, but also keeps
 * the PWA's app-icon badge (Badging API) in sync with the unread count, and
 * listens for the service worker's "set-badge" postMessage -- pushed on a
 * background `push` event so the badge stays current even if this hook's
 * own poll hasn't fired yet.
 */
export function useNotificationCount(): number {
  const { isAuthenticated } = useAuth();
  const isVisible = usePageVisibility();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['notificationCount'],
    queryFn: notifications.unreadCount,
    enabled: isAuthenticated && isVisible,
    refetchInterval: isVisible ? 30000 : false,
    staleTime: 3000,
  });

  const count = data?.count ?? 0;

  useEffect(() => {
    if (!('setAppBadge' in navigator)) return;
    if (count > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (navigator as any).setAppBadge(count).catch(() => {});
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (navigator as any).clearAppBadge?.().catch(() => {});
    }
  }, [count]);

  useEffect(() => {
    if (!isAuthenticated || !('serviceWorker' in navigator)) return;

    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === 'set-badge') {
        queryClient.setQueryData(['notificationCount'], { count: event.data.count });
      }
    };
    navigator.serviceWorker.addEventListener('message', onMessage);
    return () => navigator.serviceWorker.removeEventListener('message', onMessage);
  }, [isAuthenticated, queryClient]);

  return count;
}
