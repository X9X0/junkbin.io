import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, XCircle, ShieldCheck, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '../context/AuthContext';
import { productComponents } from '../api/endpoints';
import type { ProductComponent } from '../types';

interface Props {
  pc: ProductComponent;
  productId: string;
  compact?: boolean;
}

export default function ComponentVoteButtons({ pc, productId, compact }: Props) {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  const isOwnMapping = user && pc.created_by?.id === user.id;
  const canVote = isAuthenticated && !isOwnMapping;

  const voteMutation = useMutation({
    mutationFn: ({ voteType }: { voteType: 'confirm' | 'dispute' }) => {
      // Toggle off if clicking same vote type
      if (pc.current_user_vote === voteType) {
        return productComponents.removeVote(pc.id);
      }
      return productComponents.vote(pc.id, voteType);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId, 'components'] });
    },
  });

  return (
    <div className={clsx('flex items-center', compact ? 'gap-1.5' : 'gap-2')}>
      {/* Verified badge */}
      {pc.is_verified && (
        <span className={clsx(
          'inline-flex items-center gap-1 text-cyber-green',
          compact ? 'text-[10px]' : 'text-xs'
        )}>
          <ShieldCheck className={compact ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
          {!compact && <span className="font-mono">VERIFIED</span>}
        </span>
      )}

      {/* Needs review badge */}
      {pc.needs_review && !pc.is_verified && (
        <span className={clsx(
          'inline-flex items-center gap-1 text-cyber-yellow',
          compact ? 'text-[10px]' : 'text-xs'
        )}>
          <AlertTriangle className={compact ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
          {!compact && <span className="font-mono">REVIEW</span>}
        </span>
      )}

      {/* Confirm button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (canVote) voteMutation.mutate({ voteType: 'confirm' });
        }}
        disabled={!canVote || voteMutation.isPending}
        className={clsx(
          'inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 transition-all border',
          compact ? 'text-[10px]' : 'text-xs',
          pc.current_user_vote === 'confirm'
            ? 'bg-cyber-green/20 border-cyber-green/50 text-cyber-green'
            : 'border-transparent text-gray-500 hover:text-cyber-green hover:border-cyber-green/30',
          (!canVote || voteMutation.isPending) && 'opacity-50 cursor-not-allowed'
        )}
        title={!isAuthenticated ? 'Log in to vote' : isOwnMapping ? 'Cannot vote on own mapping' : 'Confirm this mapping'}
      >
        <CheckCircle className={compact ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
        {pc.confirm_count > 0 && <span>{pc.confirm_count}</span>}
      </button>

      {/* Dispute button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (canVote) voteMutation.mutate({ voteType: 'dispute' });
        }}
        disabled={!canVote || voteMutation.isPending}
        className={clsx(
          'inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 transition-all border',
          compact ? 'text-[10px]' : 'text-xs',
          pc.current_user_vote === 'dispute'
            ? 'bg-red-400/20 border-red-400/50 text-red-400'
            : 'border-transparent text-gray-500 hover:text-red-400 hover:border-red-400/30',
          (!canVote || voteMutation.isPending) && 'opacity-50 cursor-not-allowed'
        )}
        title={!isAuthenticated ? 'Log in to vote' : isOwnMapping ? 'Cannot vote on own mapping' : 'Dispute this mapping'}
      >
        <XCircle className={compact ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
        {pc.dispute_count > 0 && <span>{pc.dispute_count}</span>}
      </button>
    </div>
  );
}
