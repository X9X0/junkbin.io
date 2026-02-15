import {
  Gift,
  Zap,
  Crown,
  Shield,
  Star,
  Rocket,
  FileText,
  Archive,
  BookOpen,
  Award,
} from 'lucide-react';
import type { Badge } from '../types';
import clsx from 'clsx';

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  gift: Gift,
  zap: Zap,
  crown: Crown,
  shield: Shield,
  star: Star,
  rocket: Rocket,
  'file-text': FileText,
  archive: Archive,
  'book-open': BookOpen,
};

const COLOR_MAP: Record<string, { text: string; border: string; bg: string }> = {
  cyan: { text: 'text-cyber-cyan', border: 'border-cyber-cyan/30', bg: 'bg-cyber-cyan/10' },
  pink: { text: 'text-cyber-pink', border: 'border-cyber-pink/30', bg: 'bg-cyber-pink/10' },
  yellow: { text: 'text-cyber-yellow', border: 'border-cyber-yellow/30', bg: 'bg-cyber-yellow/10' },
  green: { text: 'text-cyber-green', border: 'border-cyber-green/30', bg: 'bg-cyber-green/10' },
  purple: { text: 'text-purple-400', border: 'border-purple-400/30', bg: 'bg-purple-400/10' },
};

interface BadgeChipProps {
  badge: Badge;
  size?: 'sm' | 'md';
}

export function BadgeChip({ badge, size = 'sm' }: BadgeChipProps) {
  const Icon = ICON_MAP[badge.icon] || Award;
  const colors = COLOR_MAP[badge.color] || COLOR_MAP.cyan;

  return (
    <div
      className={clsx(
        'inline-flex items-center gap-1 font-mono border',
        colors.text, colors.border, colors.bg,
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'
      )}
      title={`${badge.name}: ${badge.description}`}
    >
      <Icon className={size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
      {badge.name.toUpperCase()}
    </div>
  );
}

interface BadgeGridProps {
  badges: Badge[];
  size?: 'sm' | 'md';
  emptyMessage?: string;
}

export function BadgeGrid({ badges, size = 'md', emptyMessage }: BadgeGridProps) {
  if (!badges || badges.length === 0) {
    return emptyMessage ? (
      <span className="text-xs text-gray-600">{emptyMessage}</span>
    ) : null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {badges.map((badge) => (
        <BadgeChip key={badge.slug} badge={badge} size={size} />
      ))}
    </div>
  );
}
