import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { users } from '../api/endpoints';
import { Trophy, Shield, Star, Crown } from 'lucide-react';
import clsx from 'clsx';
import Pagination from '../components/Pagination';
import { BadgeChip } from '../components/BadgeDisplay';
import type { Badge } from '../types';
import { useTranslation } from 'react-i18next';

const PAGE_SIZE = 20;

const rankColors = [
  'text-yellow-400 border-yellow-400/50 bg-yellow-400/10',   // Gold - #1
  'text-gray-300 border-gray-300/50 bg-gray-300/10',          // Silver - #2
  'text-orange-400 border-orange-400/50 bg-orange-400/10',    // Bronze - #3
];

export default function Leaderboard() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data, isLoading } = useQuery({
    queryKey: ['leaderboard', { page }],
    queryFn: () => users.list({ page }),
  });

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 0;

  const handlePageChange = (newPage: number) => {
    const newParams = new URLSearchParams(searchParams);
    if (newPage > 1) {
      newParams.set('page', String(newPage));
    } else {
      newParams.delete('page');
    }
    setSearchParams(newParams);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <Trophy className="h-7 w-7 text-cyber-yellow" />
        <h1 className="font-display text-2xl md:text-3xl font-bold text-white">
          LEADER<span className="text-cyber-yellow">BOARD</span>
        </h1>
      </div>
      <p className="text-gray-500 font-mono text-sm mb-8">
        // {t('community.subtitle')}
      </p>

      {/* Stats bar */}
      {data && (
        <div className="flex items-center gap-6 mb-6 px-4 py-3 border border-cyber-light/20 bg-cyber-dark/50">
          <div className="flex items-center gap-2">
            <span className="text-gray-500 font-mono text-xs">{t('community.total_contributors')}</span>
            <span className="text-cyber-yellow font-mono font-bold">{data.count}</span>
          </div>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-16 bg-cyber-gray/50 border border-cyber-light/10 animate-pulse" />
          ))}
        </div>
      ) : data?.results?.length ? (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            <div className="grid grid-cols-[60px_1fr_100px_100px_minmax(0,180px)_100px] gap-2 px-4 py-2 text-gray-500 font-mono text-xs border-b border-cyber-light/30">
              <span>{t('community.col_rank')}</span>
              <span>{t('community.col_user')}</span>
              <span className="text-right">{t('community.col_reputation')}</span>
              <span className="text-right">{t('community.col_contributions')}</span>
              <span className="text-center">{t('community.col_badges')}</span>
              <span className="text-right">{t('community.col_joined')}</span>
            </div>

            <div className="space-y-1 mt-1">
              {data.results.map((user: any, index: number) => {
                const rank = (page - 1) * PAGE_SIZE + index + 1;
                const isTopThree = rank <= 3 && page === 1;

                return (
                  <Link
                    key={user.id}
                    to={`/users/${user.id}`}
                    className={clsx(
                      'grid grid-cols-[60px_1fr_100px_100px_minmax(0,180px)_100px] gap-2 items-center px-4 border transition-colors',
                      isTopThree
                        ? clsx('py-4 border-l-2', rankColors[rank - 1])
                        : 'py-3 border-cyber-light/10 hover:border-cyber-light/30 bg-cyber-dark/30'
                    )}
                  >
                    {/* Rank */}
                    <div className="flex items-center gap-1">
                      {rank <= 3 ? (
                        <Crown className={clsx('h-5 w-5', rank === 1 ? 'text-yellow-400' : rank === 2 ? 'text-gray-300' : 'text-orange-400')} />
                      ) : (
                        <span className="text-gray-500 font-mono text-sm pl-1">#{rank}</span>
                      )}
                    </div>

                    {/* User */}
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-cyber-gray border border-cyber-light/30 flex items-center justify-center flex-shrink-0 overflow-hidden">
                        {user.avatar ? (
                          <img src={user.avatar} alt="" className="w-full h-full object-cover rounded-full" />
                        ) : (
                          <span className="text-gray-500 font-mono text-xs">{user.username?.charAt(0).toUpperCase()}</span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <span className={clsx('font-mono text-sm truncate block', isTopThree ? 'text-white font-bold' : 'text-gray-300')}>
                          {user.display_name || user.username}
                        </span>
                        {user.location && (
                          <span className="text-gray-600 text-xs truncate block">{user.location}</span>
                        )}
                      </div>
                    </div>

                    {/* Reputation */}
                    <div className="text-right">
                      <span className={clsx('font-mono text-sm', isTopThree ? 'text-cyber-yellow font-bold' : 'text-cyber-cyan')}>
                        {user.reputation_score.toLocaleString()}
                      </span>
                    </div>

                    {/* Contributions */}
                    <div className="text-right">
                      <span className="text-gray-300 font-mono text-sm">
                        {user.contribution_count.toLocaleString()}
                      </span>
                    </div>

                    {/* Badges */}
                    <div className="flex items-center justify-center gap-1 flex-wrap overflow-hidden">
                      {user.badges && user.badges.length > 0 ? (
                        <>
                          {user.badges.slice(0, 3).map((badge: Badge) => (
                            <BadgeChip key={badge.slug} badge={badge} size="sm" />
                          ))}
                          {user.badges.length > 3 && (
                            <span className="text-gray-500 font-mono text-[10px]">
                              +{user.badges.length - 3}
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="text-gray-600 font-mono text-xs">&mdash;</span>
                      )}
                    </div>

                    {/* Joined */}
                    <div className="text-right">
                      <span className="text-gray-500 font-mono text-xs">
                        {new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-2">
            {data.results.map((user: any, index: number) => {
              const rank = (page - 1) * PAGE_SIZE + index + 1;
              const isTopThree = rank <= 3 && page === 1;

              return (
                <Link
                  key={user.id}
                  to={`/users/${user.id}`}
                  className={clsx(
                    'block p-4 border transition-colors',
                    isTopThree
                      ? clsx('border-l-2', rankColors[rank - 1])
                      : 'border-cyber-light/10 bg-cyber-dark/30'
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1 w-8">
                        {rank <= 3 ? (
                          <Crown className={clsx('h-5 w-5', rank === 1 ? 'text-yellow-400' : rank === 2 ? 'text-gray-300' : 'text-orange-400')} />
                        ) : (
                          <span className="text-gray-500 font-mono text-sm">#{rank}</span>
                        )}
                      </div>
                      <div className="w-8 h-8 rounded-full bg-cyber-gray border border-cyber-light/30 flex items-center justify-center overflow-hidden">
                        {user.avatar ? (
                          <img src={user.avatar} alt="" className="w-full h-full object-cover rounded-full" />
                        ) : (
                          <span className="text-gray-500 font-mono text-xs">{user.username?.charAt(0).toUpperCase()}</span>
                        )}
                      </div>
                      <span className={clsx('font-mono text-sm', isTopThree ? 'text-white font-bold' : 'text-gray-300')}>
                        {user.display_name || user.username}
                      </span>
                    </div>
                    {user.is_trusted && (
                      <Shield className="h-4 w-4 text-cyber-green" />
                    )}
                  </div>
                  <div className="flex items-center gap-4 ml-11 text-xs font-mono">
                    <span className="text-cyber-cyan">
                      <Star className="h-3 w-3 inline mr-1" />
                      {user.reputation_score.toLocaleString()} rep
                    </span>
                    <span className="text-gray-400">
                      {user.contribution_count} contributions
                    </span>
                  </div>
                  {user.badges && user.badges.length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap ml-11 mt-2">
                      {user.badges.slice(0, 3).map((badge: Badge) => (
                        <BadgeChip key={badge.slug} badge={badge} size="sm" />
                      ))}
                      {user.badges.length > 3 && (
                        <span className="text-gray-500 font-mono text-[10px]">
                          +{user.badges.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Pagination */}
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            color="cyan"
            className="mt-8"
          />
        </>
      ) : (
        <div className="text-center py-16">
          <Trophy className="h-12 w-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 font-mono">{t('community.no_contributors')}</p>
        </div>
      )}
    </div>
  );
}
