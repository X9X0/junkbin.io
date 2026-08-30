import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import { messaging } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { usePageVisibility } from './usePageVisibility';

export function useUnreadCount(): number {
  const { isAuthenticated } = useAuth();
  const isVisible = usePageVisibility();
  const location = useLocation();

  const isMessagesPage = location.pathname.startsWith('/messages');
  const interval = isMessagesPage ? 10000 : 30000;

  const { data } = useQuery({
    queryKey: ['unreadCount'],
    queryFn: messaging.unreadCount,
    enabled: isAuthenticated && isVisible,
    refetchInterval: isVisible ? interval : false,
    staleTime: 3000,
  });

  return data?.unread_count ?? 0;
}
