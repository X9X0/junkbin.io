import clsx from 'clsx';

interface MatchPercentageBarProps {
  percentage: number;
  className?: string;
  showLabel?: boolean;
}

export default function MatchPercentageBar({
  percentage,
  className,
  showLabel = true,
}: MatchPercentageBarProps) {
  const color =
    percentage >= 67
      ? 'bg-cyber-green'
      : percentage >= 34
        ? 'bg-cyber-yellow'
        : 'bg-cyber-pink';

  const textColor =
    percentage >= 67
      ? 'text-cyber-green'
      : percentage >= 34
        ? 'text-cyber-yellow'
        : 'text-cyber-pink';

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <div className="flex-1 h-2 bg-cyber-dark border border-cyber-light/30 rounded-sm overflow-hidden">
        <div
          className={clsx('h-full transition-all duration-500', color)}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      {showLabel && (
        <span className={clsx('text-xs font-mono font-bold min-w-[3rem] text-right', textColor)}>
          {Math.round(percentage)}%
        </span>
      )}
    </div>
  );
}
