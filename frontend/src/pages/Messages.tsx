import { Link, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { messaging } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { MessageSquare, Plus, Loader2 } from 'lucide-react';
import clsx from 'clsx';

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function Messages() {
  const { t } = useTranslation();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => messaging.conversations(),
    enabled: isAuthenticated,
    refetchInterval: 5000,
  });

  if (!authLoading && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const conversations = data?.results ?? [];

  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-4 flex flex-col" style={{ height: 'calc(100vh - 4rem)', overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
            <MessageSquare className="h-6 w-6 text-cyber-cyan" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-wider text-white">
              {t('messages.title')}
            </h1>
            <p className="text-xs font-mono text-gray-500">
              {data ? t('messages.count_conversations', { count: data.count }) : ''}
            </p>
          </div>
        </div>
        <Link
          to="/messages/new"
          className="btn-cyber flex items-center gap-2 text-sm py-1.5"
        >
          <Plus className="h-4 w-4" />
          {t('messages.new_btn')}
        </Link>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto min-h-0">
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card-cyber p-4 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-cyber-light/20" />
                <div className="flex-1">
                  <div className="h-4 w-32 bg-cyber-light/20 rounded mb-2" />
                  <div className="h-3 w-48 bg-cyber-light/10 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : conversations.length === 0 ? (
        <div className="text-center py-16 card-cyber">
          <MessageSquare className="h-16 w-16 text-gray-600 mx-auto mb-4" />
          <h2 className="font-display text-lg text-gray-400 mb-2">{t('messages.no_conversations')}</h2>
          <p className="text-sm text-gray-500 font-mono">
            {t('messages.no_conversations_desc')}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {conversations.map((conv) => (
            <Link
              key={conv.id}
              to={`/messages/${conv.id}`}
              className={clsx(
                'block card-cyber p-4 hover:border-cyber-cyan/50 transition-colors',
                conv.unread_count > 0 && 'border-cyber-cyan/30'
              )}
            >
              <div className="flex items-center gap-3">
                {/* Avatar */}
                <div className={clsx(
                  'h-10 w-10 rounded-full flex items-center justify-center font-mono font-bold text-sm flex-shrink-0',
                  conv.unread_count > 0
                    ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50'
                    : 'bg-cyber-light/20 text-gray-400 border border-cyber-light/30'
                )}>
                  {conv.other_participant.username.charAt(0).toUpperCase()}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className={clsx(
                      'font-mono text-sm truncate',
                      conv.unread_count > 0 ? 'text-white font-bold' : 'text-gray-300'
                    )}>
                      {conv.other_participant.username}
                      {conv.other_participant.is_trusted && (
                        <span className="ml-1 text-[10px] text-cyber-green">[TRUSTED]</span>
                      )}
                      {conv.other_participant.is_moderator && (
                        <span className="ml-1 text-[10px] text-cyber-yellow">[MOD]</span>
                      )}
                    </span>
                    <span className="text-[11px] text-gray-500 font-mono flex-shrink-0 ml-2">
                      {conv.last_message ? timeAgo(conv.last_message.created_at) : timeAgo(conv.updated_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <p className={clsx(
                      'text-sm truncate flex-1',
                      conv.unread_count > 0 ? 'text-gray-300' : 'text-gray-500'
                    )}>
                      {conv.last_message?.content ?? 'No messages yet'}
                    </p>
                    {conv.unread_count > 0 && (
                      <span className="min-w-[20px] h-5 flex items-center justify-center rounded-full bg-cyber-pink text-[10px] font-mono font-bold text-white px-1.5 flex-shrink-0">
                        {conv.unread_count > 99 ? '99+' : conv.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
      </div>
    </div>
  );
}
