import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { users, messaging } from '../api/endpoints';
import type { PublicUser } from '../types';
import {
  ArrowLeft,
  Search,
  Send,
  Loader2,
  X,
  Shield,
  Award,
  User as UserIcon,
} from 'lucide-react';

export default function NewConversation() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated } = useAuth();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState<PublicUser | null>(null);
  const [content, setContent] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  const prefillUserId = searchParams.get('to');

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Prefill recipient from ?to= param
  const { data: prefillUser } = useQuery({
    queryKey: ['user-prefill', prefillUserId],
    queryFn: () => users.get(prefillUserId!),
    enabled: !!prefillUserId && !selectedUser,
  });

  useEffect(() => {
    if (prefillUser && !selectedUser) {
      setSelectedUser(prefillUser);
    }
  }, [prefillUser, selectedUser]);

  // Search users
  const { data: searchResults, isFetching: isSearching } = useQuery({
    queryKey: ['user-search', debouncedQuery],
    queryFn: () => users.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2 && !selectedUser,
  });

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (data: { recipient_id: string; content: string }) =>
      messaging.send(data),
    onSuccess: (response) => {
      const conversationId = response.conversation_id;
      if (conversationId) {
        navigate(`/messages/${conversationId}`, { replace: true });
      } else {
        navigate('/messages', { replace: true });
      }
    },
  });

  const handleSend = useCallback(() => {
    if (!selectedUser || !content.trim() || sendMutation.isPending) return;
    sendMutation.mutate({
      recipient_id: selectedUser.id,
      content: content.trim(),
    });
  }, [selectedUser, content, sendMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSelectUser = (user: PublicUser) => {
    setSelectedUser(user);
    setSearchQuery('');
    setDebouncedQuery('');
    setShowDropdown(false);
    textareaRef.current?.focus();
  };

  const handleClearRecipient = () => {
    setSelectedUser(null);
    setSearchQuery('');
    setDebouncedQuery('');
  };

  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-3xl px-4">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link
            to="/messages"
            className="text-gray-400 hover:text-cyber-cyan transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="font-display text-xl font-bold text-white">
            NEW <span className="text-cyber-cyan">MESSAGE</span>
          </h1>
        </div>

        <div className="card-cyber p-6 space-y-6">
          {/* Recipient field */}
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-2">
              TO:
            </label>

            {selectedUser ? (
              <div className="flex items-center gap-3 p-3 bg-cyber-dark border border-cyber-light/30 rounded">
                <div className="w-8 h-8 bg-cyber-cyan/20 border border-cyber-cyan/50 flex items-center justify-center flex-shrink-0">
                  {selectedUser.avatar ? (
                    <img
                      src={selectedUser.avatar}
                      alt={selectedUser.username}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-sm font-bold text-cyber-cyan">
                      {selectedUser.username[0].toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-white truncate">
                      {selectedUser.display_name || selectedUser.username}
                    </span>
                    {selectedUser.is_trusted && (
                      <Shield className="h-3 w-3 text-cyber-green flex-shrink-0" />
                    )}
                  </div>
                  {selectedUser.display_name && selectedUser.display_name !== selectedUser.username && (
                    <span className="text-xs text-gray-500 font-mono">
                      @{selectedUser.username}
                    </span>
                  )}
                </div>
                <button
                  onClick={handleClearRecipient}
                  className="text-gray-500 hover:text-cyber-pink transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div className="relative">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setShowDropdown(true);
                    }}
                    onFocus={() => setShowDropdown(true)}
                    placeholder="Search for a user..."
                    className="input-cyber w-full pl-10"
                    autoFocus
                  />
                  {isSearching && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-cyber-cyan animate-spin" />
                  )}
                </div>

                {/* Autocomplete dropdown */}
                {showDropdown && debouncedQuery.length >= 2 && (
                  <div className="absolute z-10 w-full mt-1 bg-cyber-dark border border-cyber-light/30 shadow-lg max-h-60 overflow-y-auto">
                    {searchResults?.results && searchResults.results.length > 0 ? (
                      searchResults.results.map((user) => (
                        <button
                          key={user.id}
                          onClick={() => handleSelectUser(user)}
                          className="w-full flex items-center gap-3 p-3 hover:bg-cyber-cyan/10 transition-colors text-left border-b border-cyber-light/10 last:border-b-0"
                        >
                          <div className="w-8 h-8 bg-cyber-cyan/20 border border-cyber-cyan/50 flex items-center justify-center flex-shrink-0">
                            {user.avatar ? (
                              <img
                                src={user.avatar}
                                alt={user.username}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <span className="text-sm font-bold text-cyber-cyan">
                                {user.username[0].toUpperCase()}
                              </span>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm text-white truncate">
                                {user.display_name || user.username}
                              </span>
                              {user.is_trusted && (
                                <Shield className="h-3 w-3 text-cyber-green flex-shrink-0" />
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1 text-xs text-gray-500 flex-shrink-0">
                            <Award className="h-3 w-3" />
                            {user.reputation_score}
                          </div>
                        </button>
                      ))
                    ) : !isSearching ? (
                      <div className="p-4 text-center">
                        <UserIcon className="h-6 w-6 text-gray-600 mx-auto mb-2" />
                        <p className="text-gray-500 text-sm font-mono">
                          No users found
                        </p>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Message compose area */}
          <div>
            <label className="block text-xs font-mono text-gray-500 mb-2">
              MESSAGE:
            </label>

            {sendMutation.isError && (
              <div className="mb-3 p-3 bg-cyber-pink/10 border border-cyber-pink/30 text-sm text-cyber-pink font-mono">
                {(sendMutation.error as any)?.response?.data?.detail ||
                  'Failed to send message. Please try again.'}
              </div>
            )}

            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                selectedUser
                  ? `Write a message to ${selectedUser.display_name || selectedUser.username}...`
                  : 'Select a recipient first...'
              }
              disabled={!selectedUser}
              rows={5}
              maxLength={5000}
              className="input-cyber w-full resize-none disabled:opacity-50 disabled:cursor-not-allowed"
            />

            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-gray-600 font-mono">
                Ctrl+Enter to send
              </span>
              <span className="text-xs text-gray-600 font-mono">
                {content.length}/5000
              </span>
            </div>
          </div>

          {/* Send button */}
          <div className="flex justify-end">
            <button
              onClick={handleSend}
              disabled={
                !selectedUser || !content.trim() || sendMutation.isPending
              }
              className="btn-cyber flex items-center gap-2 px-6 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sendMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              SEND MESSAGE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
