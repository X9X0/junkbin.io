import { Link } from 'react-router-dom';
import { Clock, ShieldCheck, TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ModerationNoticeProps {
  itemLabel: string;
  viewLink: string;
  onSubmitAnother: () => void;
}

/**
 * Shown after a user submits content that requires moderator review.
 * Thresholds match backend settings:
 *   TRUSTED_USER_CONTRIBUTION_THRESHOLD = 50
 *   TRUSTED_USER_MIN_REPUTATION          = 100
 */
export default function ModerationNotice({ itemLabel, viewLink, onSubmitAnother }: ModerationNoticeProps) {
  const { t } = useTranslation();

  return (
    <div className="card-cyber p-6 space-y-5">
      {/* Success header */}
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-8 w-8 text-cyber-green shrink-0" />
        <div>
          <p className="text-cyber-green font-display font-bold text-lg tracking-wider">
            SUBMISSION RECEIVED
          </p>
          <p className="text-gray-400 text-sm mt-0.5">
            {itemLabel} is now in the moderation queue.
          </p>
        </div>
      </div>

      {/* Explanation panels */}
      <div className="space-y-3 text-sm text-gray-400 border border-cyber-light/20 bg-cyber-dark/50 p-4">
        <div className="flex items-start gap-3">
          <Clock className="h-4 w-4 text-cyber-cyan mt-0.5 shrink-0" />
          <p>
            A moderator will review your submission shortly. Once approved it will be
            visible to all users — usually within a few hours.
          </p>
        </div>
        <div className="flex items-start gap-3">
          <TrendingUp className="h-4 w-4 text-cyber-yellow mt-0.5 shrink-0" />
          <p>
            After{' '}
            <span className="text-white font-mono">25 approved contributions</span>
            {' '}and{' '}
            <span className="text-white font-mono">50 reputation points</span>,
            your submissions will be published instantly — no moderation required.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4 flex-wrap">
        <Link to={viewLink} className="btn-cyber text-sm">
          VIEW SUBMISSION
        </Link>
        <button
          onClick={onSubmitAnother}
          className="text-sm text-gray-400 hover:text-white transition-colors font-mono"
        >
          SUBMIT ANOTHER →
        </button>
      </div>
    </div>
  );
}
