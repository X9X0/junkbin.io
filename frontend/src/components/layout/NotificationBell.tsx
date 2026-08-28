import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { notifications } from '../../api/endpoints';
import { useNotificationCount } from '../../hooks/useNotificationCount';
import type { AppNotification } from '../../types';

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

interface NotificationBellProps {
  /** Matches the icon sizing/spacing of the message icon at each responsive breakpoint. */
  iconClassName?: string;
  badgeClassName?: string;
}

export default function NotificationBell({
  iconClassName = 'h-5 w-5',
  badgeClassName = 'absolute -top-1 -right-1 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-cyber-pink text-[10px] font-mono font-bold text-white px-1',
}: NotificationBellProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const unreadCount = useNotificationCount();
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data } = useQuery({
    queryKey: ['notificationList'],
    queryFn: () => notifications.list({ page_size: 8 }),
    enabled: isOpen,
    staleTime: 0,
  });

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleItemClick = async (n: AppNotification) => {
    setIsOpen(false);
    if (!n.is_read) {
      await notifications.markRead(n.id);
      queryClient.invalidateQueries({ queryKey: ['notificationCount'] });
      queryClient.invalidateQueries({ queryKey: ['notificationList'] });
    }
    if (n.url) navigate(n.url);
  };

  const handleMarkAllRead = async () => {
    await notifications.markAllRead();
    queryClient.invalidateQueries({ queryKey: ['notificationCount'] });
    queryClient.invalidateQueries({ queryKey: ['notificationList'] });
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className={`relative text-gray-400 hover:text-cyber-cyan transition-colors p-1`}
        title={t('nav.notifications', 'Notifications')}
      >
        <Bell className={iconClassName} />
        {unreadCount > 0 && (
          <span className={badgeClassName}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-cyber-dark border border-cyber-light/30 shadow-lg z-50">
          <div className="flex items-center justify-between px-3 py-2 border-b border-cyber-light/20">
            <span className="font-mono text-sm text-gray-300">
              {t('nav.notifications', 'Notifications')}
            </span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-cyber-cyan hover:underline font-mono"
              >
                {t('nav.markAllRead', 'Mark all read')}
              </button>
            )}
          </div>

          {!data?.results.length ? (
            <div className="px-3 py-6 text-center text-sm text-gray-500 font-mono">
              {t('nav.noNotifications', 'No notifications yet')}
            </div>
          ) : (
            data.results.map((n) => (
              <button
                key={n.id}
                onClick={() => handleItemClick(n)}
                className={`w-full text-left px-3 py-2 border-b border-cyber-light/10 hover:bg-cyber-light/10 transition-colors ${
                  n.is_read ? 'opacity-60' : ''
                }`}
              >
                <div className="text-sm text-gray-200 font-mono">{n.title}</div>
                {n.body && (
                  <div className="text-xs text-gray-500 truncate mt-0.5">{n.body}</div>
                )}
                <div className="text-[10px] text-gray-600 mt-1">{timeAgo(n.created_at)}</div>
              </button>
            ))
          )}

          <button
            onClick={() => {
              setIsOpen(false);
              navigate('/notifications');
            }}
            className="w-full text-center px-3 py-2 text-xs text-cyber-cyan hover:underline font-mono"
          >
            {t('nav.viewAllNotifications', 'View all')}
          </button>
        </div>
      )}
    </div>
  );
}
