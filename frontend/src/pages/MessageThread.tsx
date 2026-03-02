import { useState, useRef, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { messaging } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { ArrowLeft, Send, Loader2, Flag, Ban, ShieldOff, ChevronUp, Paperclip, X, FileText, Download } from 'lucide-react';
import ReportModal from '../components/ReportModal';
import clsx from 'clsx';
import type { MessageAttachment } from '../types';

const MAX_FILES = 5;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf', 'zip', 'txt', 'csv']);

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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
  const queryClient = useQueryClient();
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [content, setContent] = useState('');
  const [page, setPage] = useState(1);
  const [reportMessageId, setReportMessageId] = useState<string | null>(null);
  const [showReportUser, setShowReportUser] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [lightbox, setLightbox] = useState<{ url: string; filename: string } | null>(null);

  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setLightbox(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightbox]);

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
    mutationFn: ({ text, files }: { text: string; files: File[] }) =>
      messaging.send({ conversation_id: conversationId, content: text, files }),
    onSuccess: () => {
      setContent('');
      setPendingFiles([]);
      setFileError(null);
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
    if ((!trimmed && pendingFiles.length === 0) || sendMutation.isPending) return;
    sendMutation.mutate({ text: trimmed, files: pendingFiles });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    e.target.value = '';
    const combined = [...pendingFiles, ...selected];

    if (combined.length > MAX_FILES) {
      setFileError(`Max ${MAX_FILES} attachments per message.`);
      return;
    }
    for (const f of selected) {
      const ext = f.name.includes('.') ? f.name.split('.').pop()!.toLowerCase() : '';
      if (!ALLOWED_EXTENSIONS.has(ext)) {
        setFileError(`File type .${ext} is not allowed.`);
        return;
      }
      if (f.size > MAX_FILE_SIZE) {
        setFileError(`${f.name} exceeds the 10 MB size limit.`);
        return;
      }
    }
    setFileError(null);
    setPendingFiles(combined);
  };

  const removeFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
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
                  {msg.content && (
                    <p className="text-sm text-gray-200 whitespace-pre-wrap break-words">
                      {msg.content}
                    </p>
                  )}
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className={clsx('flex flex-col gap-2', msg.content && 'mt-2')}>
                      {msg.attachments.map((att: MessageAttachment) =>
                        att.is_image ? (
                          <div
                            key={att.id}
                            className="relative group/img cursor-zoom-in inline-block"
                            onClick={() => setLightbox({ url: att.url, filename: att.original_filename })}
                          >
                            <img
                              src={att.url}
                              alt={att.original_filename}
                              className="max-w-xs max-h-64 object-contain border border-cyber-light/20"
                            />
                            <a
                              href={att.url}
                              download={att.original_filename}
                              onClick={(e) => e.stopPropagation()}
                              title="Download"
                              className="absolute bottom-1 right-1 opacity-0 group-hover/img:opacity-100 bg-black/60 p-1 transition-opacity"
                            >
                              <Download className="h-3 w-3 text-white" />
                            </a>
                          </div>
                        ) : (
                          <a
                            key={att.id}
                            href={att.url}
                            download={att.original_filename}
                            className="flex items-center gap-2 px-3 py-2 border border-cyber-light/30 hover:border-cyber-cyan/50 transition-colors text-xs font-mono text-gray-300 hover:text-cyber-cyan"
                          >
                            <FileText className="h-4 w-4 shrink-0" />
                            <span className="truncate">{att.original_filename}</span>
                            <span className="text-gray-500 shrink-0">{formatBytes(att.file_size)}</span>
                            <Download className="h-3 w-3 shrink-0 ml-auto" />
                          </a>
                        )
                      )}
                    </div>
                  )}
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
        {(sendMutation.isError || fileError) && (
          <div className="mb-3 p-2 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-xs font-mono">
            {fileError ?? 'Failed to send message. Please try again.'}
          </div>
        )}
        {/* Pending file previews */}
        {pendingFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {pendingFiles.map((f, i) => {
              const isImage = f.type.startsWith('image/');
              return (
                <div
                  key={i}
                  className="relative flex items-center gap-1 border border-cyber-light/30 bg-cyber-dark px-2 py-1 text-xs font-mono text-gray-300"
                >
                  {isImage ? (
                    <img
                      src={URL.createObjectURL(f)}
                      alt={f.name}
                      className="h-10 w-10 object-cover"
                    />
                  ) : (
                    <FileText className="h-4 w-4 text-gray-500" />
                  )}
                  <span className="max-w-[120px] truncate">{f.name}</span>
                  <span className="text-gray-600">{formatBytes(f.size)}</span>
                  <button
                    onClick={() => removeFile(i)}
                    className="ml-1 text-gray-500 hover:text-cyber-pink transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
        <div className="flex gap-3">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.zip,.txt,.csv"
            className="hidden"
            onChange={handleFileChange}
          />
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={4}
            maxLength={5000}
            className="input-cyber flex-1 resize-none text-sm"
          />
          {/* Button stack: paperclip above send */}
          <div className="flex flex-col gap-2 self-end">
            <button
              onClick={() => fileInputRef.current?.click()}
              title="Attach files"
              className="btn-cyber px-4"
            >
              <Paperclip className="h-4 w-4" />
            </button>
            <button
              onClick={handleSend}
              disabled={(!content.trim() && pendingFiles.length === 0) || sendMutation.isPending}
              className={clsx(
                'btn-cyber px-4',
                ((!content.trim() && pendingFiles.length === 0) || sendMutation.isPending) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {sendMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-gray-600 font-mono">
            Ctrl+Enter to send · {pendingFiles.length}/{MAX_FILES} files
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

      {/* Image lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4"
          onClick={() => setLightbox(null)}
        >
          <div
            className="relative flex flex-col items-center gap-3 max-w-[90vw] max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setLightbox(null)}
              className="absolute -top-9 right-0 text-gray-400 hover:text-white transition-colors"
              title="Close"
            >
              <X className="h-6 w-6" />
            </button>
            <img
              src={lightbox.url}
              alt={lightbox.filename}
              className="max-w-full max-h-[80vh] object-contain"
            />
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-gray-400 truncate max-w-xs">{lightbox.filename}</span>
              <a
                href={lightbox.url}
                download={lightbox.filename}
                className="btn-cyber text-xs px-3 py-1 flex items-center gap-1.5"
              >
                <Download className="h-3 w-3" />
                Download
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
