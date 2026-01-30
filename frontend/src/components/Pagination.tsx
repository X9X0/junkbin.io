import { ChevronLeft, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  color?: 'cyan' | 'pink' | 'green';
  className?: string;
}

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  color = 'cyan',
  className,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const colorClasses = {
    cyan: {
      active: 'border-cyber-cyan bg-cyber-cyan/20 text-cyber-cyan',
      hover: 'hover:border-cyber-cyan hover:text-cyber-cyan',
    },
    pink: {
      active: 'border-cyber-pink bg-cyber-pink/20 text-cyber-pink',
      hover: 'hover:border-cyber-pink hover:text-cyber-pink',
    },
    green: {
      active: 'border-cyber-green bg-cyber-green/20 text-cyber-green',
      hover: 'hover:border-cyber-green hover:text-cyber-green',
    },
  };

  const colors = colorClasses[color];

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      onPageChange(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];

    // Always show first page
    if (currentPage > 3) {
      pages.push(1);
      if (currentPage > 4) {
        pages.push('ellipsis');
      }
    }

    // Show pages around current
    for (let i = currentPage - 2; i <= currentPage + 2; i++) {
      if (i >= 1 && i <= totalPages) {
        pages.push(i);
      }
    }

    // Always show last page
    if (currentPage < totalPages - 2) {
      if (currentPage < totalPages - 3) {
        pages.push('ellipsis');
      }
      pages.push(totalPages);
    }

    return pages;
  };

  return (
    <div className={clsx('flex items-center justify-center gap-2', className)}>
      {/* Previous button */}
      <button
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className={clsx(
          'p-2 border font-mono text-sm transition-colors',
          currentPage <= 1
            ? 'border-cyber-light/30 text-gray-600 cursor-not-allowed'
            : `border-cyber-light/50 text-gray-400 ${colors.hover}`
        )}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-5 w-5" />
      </button>

      {/* Page numbers */}
      <div className="flex items-center gap-1">
        {getPageNumbers().map((page, index) =>
          page === 'ellipsis' ? (
            <span key={`ellipsis-${index}`} className="px-2 text-gray-600">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => handlePageChange(page)}
              className={clsx(
                'px-3 py-2 border font-mono text-sm transition-colors',
                page === currentPage
                  ? colors.active
                  : `border-cyber-light/50 text-gray-400 ${colors.hover}`
              )}
              aria-label={`Page ${page}`}
              aria-current={page === currentPage ? 'page' : undefined}
            >
              {page}
            </button>
          )
        )}
      </div>

      {/* Next button */}
      <button
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className={clsx(
          'p-2 border font-mono text-sm transition-colors',
          currentPage >= totalPages
            ? 'border-cyber-light/30 text-gray-600 cursor-not-allowed'
            : `border-cyber-light/50 text-gray-400 ${colors.hover}`
        )}
        aria-label="Next page"
      >
        <ChevronRight className="h-5 w-5" />
      </button>

      {/* Page info */}
      <div className="ml-4 text-sm text-gray-500 font-mono hidden sm:block">
        Page {currentPage} of {totalPages}
      </div>
    </div>
  );
}
