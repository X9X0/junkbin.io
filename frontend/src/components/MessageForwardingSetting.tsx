import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { Forward, Loader2, Search, User as UserIcon, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { auth, users } from '../api/endpoints';
import type { PublicUser } from '../types';

/**
 * Lets a user delegate their incoming messages to another user, who sees a
 * mirrored copy and can reply on their behalf (see SendMessageView._handle_forwarding
 * on the backend). Own inbox is unaffected; the delegate's identity is never
 * exposed to the original sender.
 */
export default function MessageForwardingSetting() {
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [results, setResults] = useState<PublicUser[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery.trim()), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setIsSearching(true);
    users.search(debouncedQuery).then((res) => {
      if (!cancelled) setResults(res.results);
    }).finally(() => {
      if (!cancelled) setIsSearching(false);
    });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  const setDelegateMutation = useMutation({
    mutationFn: (delegateId: string | null) => auth.updateMe({ forward_messages_to: delegateId }),
    onSuccess: async () => {
      setSearchQuery('');
      setShowDropdown(false);
      await refreshUser();
    },
  });

  const delegate = user?.forward_messages_to_detail;

  return (
    <div className="flex items-start justify-between py-2 gap-4">
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white font-mono flex items-center gap-1.5">
          <Forward className="h-3.5 w-3.5" />
          {t('profile.forward_messages', 'Forward my messages')}
        </div>
        <div className="text-xs text-gray-500 mb-2">
          {t(
            'profile.forward_messages_desc',
            "Mirror messages you receive to a delegate, who can reply on your behalf. Your own inbox isn't affected."
          )}
        </div>

        {delegate ? (
          <div className="flex items-center gap-2 border border-cyber-light/30 bg-cyber-dark px-3 py-1.5 w-fit">
            <div className="w-6 h-6 bg-cyber-cyan/20 border border-cyber-cyan/50 flex items-center justify-center flex-shrink-0">
              {delegate.avatar ? (
                <img src={delegate.avatar} alt={delegate.username} className="w-full h-full object-cover" />
              ) : (
                <UserIcon className="h-3 w-3 text-cyber-cyan" />
              )}
            </div>
            <span className="font-mono text-sm text-white">{delegate.display_name || delegate.username}</span>
            <button
              onClick={() => setDelegateMutation.mutate(null)}
              disabled={setDelegateMutation.isPending}
              className="text-gray-500 hover:text-cyber-pink transition-colors disabled:opacity-50 ml-1"
              title={t('profile.forward_remove', 'Remove delegate')}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="relative max-w-xs">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
                placeholder={t('profile.forward_search_placeholder', 'Search for a user...')}
                className="input-cyber w-full pl-9 text-sm py-1.5"
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-cyber-cyan animate-spin" />
              )}
            </div>

            {showDropdown && debouncedQuery.length >= 2 && (
              <div className="absolute z-10 w-full mt-1 bg-cyber-dark border border-cyber-light/30 shadow-lg max-h-52 overflow-y-auto">
                {results.length > 0 ? (
                  results
                    .filter((u) => u.id !== user?.id)
                    .map((candidate) => (
                      <button
                        key={candidate.id}
                        onClick={() => setDelegateMutation.mutate(candidate.id)}
                        disabled={setDelegateMutation.isPending}
                        className="w-full flex items-center gap-2 p-2 hover:bg-cyber-cyan/10 transition-colors text-left border-b border-cyber-light/10 last:border-b-0 disabled:opacity-50"
                      >
                        <div className="w-6 h-6 bg-cyber-cyan/20 border border-cyber-cyan/50 flex items-center justify-center flex-shrink-0">
                          {candidate.avatar ? (
                            <img src={candidate.avatar} alt={candidate.username} className="w-full h-full object-cover" />
                          ) : (
                            <span className="text-xs font-bold text-cyber-cyan">
                              {candidate.username[0].toUpperCase()}
                            </span>
                          )}
                        </div>
                        <span className="font-mono text-sm text-white truncate">
                          {candidate.display_name || candidate.username}
                        </span>
                      </button>
                    ))
                ) : (
                  <div className="p-3 text-xs text-gray-500 font-mono">
                    {t('profile.forward_no_results', 'No users found')}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {setDelegateMutation.isError && (
          <div className="text-xs text-cyber-pink mt-1">
            {t('profile.forward_error', 'Could not update your delegate. Please try again.')}
          </div>
        )}
      </div>
    </div>
  );
}
