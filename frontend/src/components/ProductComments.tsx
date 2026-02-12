import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { Trash2, MessageSquare, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

function timeAgo(dateString: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

export default function ProductComments({ productId }: { productId: string }) {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [content, setContent] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['product', productId, 'comments', page],
    queryFn: () => products.comments(productId, page),
  });

  const addMutation = useMutation({
    mutationFn: (text: string) => products.addComment(productId, text),
    onSuccess: () => {
      setContent('');
      setError('');
      setPage(1);
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'comments'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.content?.[0] || err.response?.data?.detail || 'Failed to post comment.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (commentId: string) => products.deleteComment(productId, commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'comments'] });
      queryClient.invalidateQueries({ queryKey: ['product', productId] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed) return;
    addMutation.mutate(trimmed);
  };

  const canDelete = (authorId: string) => {
    if (!user) return false;
    return user.id === authorId || user.is_moderator;
  };

  return (
    <div className="space-y-6">
      {/* Add Comment Form */}
      {isAuthenticated ? (
        <div className="card-cyber p-4">
          <form onSubmit={handleSubmit}>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Share a repair tip, ask a question, or leave a note..."
              maxLength={2000}
              rows={3}
              className="input-cyber w-full resize-none"
            />
            <div className="flex items-center justify-between mt-2">
              <span className={clsx(
                'text-xs font-mono',
                content.length > 1900 ? 'text-cyber-yellow' : 'text-gray-600'
              )}>
                {content.length}/2000
              </span>
              <button
                type="submit"
                disabled={!content.trim() || addMutation.isPending}
                className="btn-cyber text-sm py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {addMutation.isPending ? 'POSTING...' : 'POST COMMENT'}
              </button>
            </div>
            {error && (
              <div className="flex items-center gap-2 mt-2 text-xs text-red-400">
                <AlertCircle className="h-3 w-3" />
                {error}
              </div>
            )}
          </form>
        </div>
      ) : (
        <div className="card-cyber p-6 text-center">
          <MessageSquare className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400 mb-3 text-sm">Log in to join the discussion.</p>
          <Link to="/login" className="btn-cyber text-sm">
            LOGIN TO COMMENT
          </Link>
        </div>
      )}

      {/* Comments List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card-cyber p-4 animate-pulse">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-cyber-light/20" />
                <div className="h-3 w-24 bg-cyber-light/20 rounded" />
              </div>
              <div className="h-3 w-full bg-cyber-light/10 rounded mb-1" />
              <div className="h-3 w-2/3 bg-cyber-light/10 rounded" />
            </div>
          ))}
        </div>
      ) : data && data.results.length > 0 ? (
        <div className="space-y-3">
          {data.results.map((comment) => (
            <div key={comment.id} className="card-cyber p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-7 h-7 rounded-full bg-cyber-cyan/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-mono text-cyber-cyan uppercase">
                      {comment.author?.username?.[0] || '?'}
                    </span>
                  </div>
                  <span className="font-mono text-sm text-white truncate">
                    {comment.author?.username || 'deleted'}
                  </span>
                  <span className="text-xs text-gray-600 flex-shrink-0">
                    {timeAgo(comment.created_at)}
                  </span>
                </div>
                {comment.author && canDelete(comment.author.id) && (
                  <button
                    onClick={() => {
                      if (confirm('Delete this comment?')) {
                        deleteMutation.mutate(comment.id);
                      }
                    }}
                    className="text-gray-600 hover:text-red-400 transition-colors flex-shrink-0 p-1"
                    title="Delete comment"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <p className="text-gray-300 text-sm mt-2 whitespace-pre-wrap break-words">
                {comment.content}
              </p>
            </div>
          ))}

          {/* Pagination */}
          {data.count > data.results.length && (
            <div className="flex justify-center gap-3 pt-2">
              {data.previous && (
                <button
                  onClick={() => setPage((p) => p - 1)}
                  className="btn-cyber text-xs py-1.5"
                >
                  NEWER
                </button>
              )}
              {data.next && (
                <button
                  onClick={() => setPage((p) => p + 1)}
                  className="btn-cyber text-xs py-1.5"
                >
                  OLDER
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <MessageSquare className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No comments yet — be the first!</p>
        </div>
      )}
    </div>
  );
}
