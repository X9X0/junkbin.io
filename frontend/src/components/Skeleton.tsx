import clsx from 'clsx';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export function Skeleton({
  className,
  variant = 'text',
  width,
  height,
  lines = 1,
}: SkeletonProps) {
  const baseClasses = 'animate-pulse bg-cyber-light/30';

  const variantClasses = {
    text: 'h-4 rounded',
    rectangular: 'rounded',
    circular: 'rounded-full',
  };

  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  if (variant === 'text' && lines > 1) {
    return (
      <div className={clsx('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={clsx(baseClasses, variantClasses.text)}
            style={{
              ...style,
              width: i === lines - 1 ? '75%' : style.width,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={clsx(baseClasses, variantClasses[variant], className)}
      style={style}
    />
  );
}

// Product card skeleton
export function ProductCardSkeleton() {
  return (
    <div className="card-cyber p-4">
      <Skeleton variant="rectangular" className="aspect-[4/3] mb-4" />
      <Skeleton width="40%" className="mb-2" />
      <Skeleton width="70%" height={20} className="mb-2" />
      <div className="flex gap-2 mt-2">
        <Skeleton width={60} height={20} />
        <Skeleton width={40} height={20} />
      </div>
    </div>
  );
}

// Component card skeleton
export function ComponentCardSkeleton() {
  return (
    <div className="card-cyber p-4">
      <Skeleton variant="rectangular" className="aspect-square mb-4" />
      <Skeleton width="30%" className="mb-2" />
      <Skeleton width="60%" height={20} className="mb-2" />
      <Skeleton width="50%" className="mt-2" />
    </div>
  );
}

// Table row skeleton
export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <tr className="border-b border-cyber-light/20">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-3 px-4">
          <Skeleton width={i === 0 ? '40%' : '60%'} />
        </td>
      ))}
    </tr>
  );
}

// Grid of product skeletons
export function ProductGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <ProductCardSkeleton key={i} />
      ))}
    </div>
  );
}

// Grid of component skeletons
export function ComponentGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <ComponentCardSkeleton key={i} />
      ))}
    </div>
  );
}

export default Skeleton;
