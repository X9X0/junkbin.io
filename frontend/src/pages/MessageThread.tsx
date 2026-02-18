import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { messaging } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { ArrowLeft, Send, Loader2, Flag, Ban, ShieldOff, ChevronUp } from 'lucide-react';
import ReportModal from '../components/ReportModal';
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

export default function MessageThread() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [content, setContent] = useState('');
  const [page, setPage] = useState(1);
  const [reportMessageId, setReportMessageId] = useState<string | null>(null);
  const [showReportUser, setShowReportUser] = useState(false);

  // Fetch conversation detail (also marks messages as read)
  const { data: conversation } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => messaging.conversation(conversationId!),
    enabled: !!conversationId,
    refetchInterval: 5000,
  });

  // Fetch messages
  const { data: messagesData, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', conversationId, page],
    queryFn: () => messaging.messages(conversationId!, { page }),
    enabled: !!conversationId,
    refetchInterval: 5000,
  });

  // Determine the other participant from the conversation detail.
  // The detail endpoint returns participant_1/participant_2 (not other_participant).
  const otherParticipant = conversation
    ? conversation.other_participant
      ?? (conversation.participant_1?.id === user?.id
        ? conversation.participant_2
        : conversation.participant_1)
    : undefined;

  // Scroll messages container to bottom on initial load and new messages
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const el = messagesContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  };

  useEffect(() => {
    if (messagesData && page === 1) {
      scrollToBottom('auto');
    }
  }, [messagesData, page]);

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (text: string) =>
      messaging.send({ conversation_id: conversationId, content: text }),
    onSuccess: () => {
      setContent('');
      queryClient.invalidateQueries({ queryKey: ['messages', conversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
      setTimeout(() => scrollToBottom(), 100);
    },
  });

  // Fetch blocked users to determine if this user is already blocked
  const { data: blockedData } = useQuery({
    queryKey: ['blocked-users'],
    queryFn: messaging.blocks,
    enabled: !!otherParticipant,
  });

  const existingBlock = blockedData?.results.find(
    (b) => b.blocked_user.id === otherParticipant?.id
  );

  // Block user mutation
  const blockMutation = useMutation({
    mutationFn: () => messaging.blockUser(otherParticipant!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocked-users'] });
    },
  });

  // Unblock user mutation
  const unblockMutation = useMutation({
    mutationFn: (blockId: string) => messaging.unblockUser(blockId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocked-users'] });
    },
  });

  const handleSend = () => {
    const trimmed = content.trim();
    if (!trimmed || sendMutation.isPending) return;
    sendMutation.mutate(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  // Messages come newest first from API, reverse for display
  const messages = [...(messagesData?.results ?? [])].reverse();
  const hasMore = !!messagesData?.next;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 flex flex-col" style={{ height: 'calc(100vh - 4rem)', overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-cyber-light/30">
        <div className="flex items-center gap-3">
          <Link
            to="/messages"
            className="p-2 text-gray-400 hover:text-cyber-cyan transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          {otherParticipant && (
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-full flex items-center justify-center font-mono font-bold text-sm bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50">
                {otherParticipant.username.charAt(0).toUpperCase()}
              </div>
              <div>
                <span className="font-mono text-sm text-white">
                  {otherParticipant.username}
                </span>
                {otherParticipant.is_trusted && (
                  <span className="ml-1 text-[10px] text-cyber-green">[TRUSTED]</span>
                )}
                {otherParticipant.is_moderator && (
                  <span className="ml-1 text-[10px] text-cyber-yellow">[MOD]</span>
                )}
              </div>
            </div>
          )}
        </div>
        {otherParticipant && (
          <div className="flex items-center gap-3">
            {existingBlock ? (
              <button
                onClick={() => unblockMutation.mutate(existingBlock.id)}
                disabled={unblockMutation.isPending}
                className="flex items-center gap-1 text-xs font-mono text-cyber-green hover:text-white transition-colors disabled:opacity-50"
                title="Unblock user"
              >
                <ShieldOff className="h-3.5 w-3.5" />
                UNBLOCK
              </button>
            ) : (
              <button
                onClick={() => {
                  if (window.confirm(`Block ${otherParticipant.username}? You will no longer be able to message each other.`)) {
                    blockMutation.mutate();
                  }
                }}
                disabled={blockMutation.isPending}
                className="flex items-center gap-1 text-xs font-mono text-gray-500 hover:text-cyber-pink transition-colors disabled:opacity-50"
                title="Block user"
              >
                <Ban className="h-3.5 w-3.5" />
                BLOCK
              </button>
            )}
            <button
              onClick={() => setShowReportUser(true)}
              className="flex items-center gap-1 text-xs font-mono text-gray-500 hover:text-cyber-yellow transition-colors"
              title="Report user"
            >
              <Flag className="h-3.5 w-3.5" />
              REPORT
            </button>
          </div>
        )}
      </div>

      {/* Messages area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto space-y-3 mb-4">
        {/* Load older button */}
        {hasMore && (
          <button
            onClick={() => setPage((p) => p + 1)}
            className="w-full py-2 text-center text-xs font-mono text-gray-500 hover:text-cyber-cyan transition-colors flex items-center justify-center gap-1"
          >
            <ChevronUp className="h-3 w-3" />
            Load older messages
          </button>
        )}

        {messagesLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-cyber-cyan" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-16 text-gray-500 text-sm font-mono">
            No messages yet. Say hello!
          </div>
        ) : (
          messages.map((msg) => {
            const isSelf = msg.sender?.id === user?.id;
            return (
              <div
                key={msg.id}
                className={clsx(
                  'flex',
                  isSelf ? 'justify-end' : 'justify-start'
                )}
              >
                <div
                  className={clsx(
                    'max-w-[75%] px-4 py-3 group relative',
                    isSelf
                      ? 'bg-cyber-cyan/10 border border-cyber-cyan/30'
                      : 'bg-cyber-dark border border-cyber-light/30'
                  )}
                >
                  <p className="text-sm text-gray-200 whitespace-pre-wrap break-words">
                    {msg.content}
                  </p>
                  <div className={clsx(
                    'flex items-center gap-2 mt-1',
                    isSelf ? 'justify-end' : 'justify-start'
                  )}>
                    <span className="text-[10px] text-gray-600 font-mono">
                      {timeAgo(msg.created_at)}
                    </span>
                  </div>
                  {/* Report button on hover for received messages */}
                  {!isSelf && (
                    <button
                      onClick={() => setReportMessageId(msg.id)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-gray-600 hover:text-cyber-yellow transition-all"
                      title="Report message"
                    >
                      <Flag className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Compose area */}
      <div className="border-t border-cyber-light/30 pt-4">
        {sendMutation.isError && (
          <div className="mb-3 p-2 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-xs font-mono">
            Failed to send message. Please try again.
          </div>
        )}
        <div className="flex gap-3">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={2}
            maxLength={5000}
            className="input-cyber flex-1 resize-none text-sm"
          />
          <button
            onClick={handleSend}
            disabled={!content.trim() || sendMutation.isPending}
            className={clsx(
              'btn-cyber px-4 self-end',
              (!content.trim() || sendMutation.isPending) && 'opacity-50 cursor-not-allowed'
            )}
          >
            {sendMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-gray-600 font-mono">
            Ctrl+Enter to send
          </span>
          <span className="text-[10px] text-gray-600 font-mono">
            {content.length}/5000
          </span>
        </div>
      </div>

      {/* Report message modal */}
      {reportMessageId && (
        <ReportModal
          isOpen={!!reportMessageId}
          onClose={() => setReportMessageId(null)}
          contentType="messaging.message"
          objectId={reportMessageId}
          itemName="Message"
        />
      )}

      {/* Report user modal */}
      {otherParticipant && (
        <ReportModal
          isOpen={showReportUser}
          onClose={() => setShowReportUser(false)}
          contentType="users.customuser"
          objectId={otherParticipant.id}
          itemName={otherParticipant.username}
        />
      )}
    </div>
  );
}
