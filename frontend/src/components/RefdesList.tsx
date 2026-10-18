import { useState } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * A BOM row's reference designators. Factory BOMs can list hundreds of positions
 * for one part (C1, C2, ... C400), so long lists show the first few and expand.
 */
export default function RefdesList({ value, limit = 8, className = '' }: { value: string; limit?: number; className?: string }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const refs = value.split(',').map((r) => r.trim()).filter(Boolean);
  if (refs.length <= limit || open) {
    return <span className={className}>{refs.join(', ')}</span>;
  }
  return (
    <span className={className} title={refs.join(', ')}>
      {refs.slice(0, limit).join(', ')}{' '}
      <button
        type="button"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}
        className="text-gray-500 hover:text-cyber-cyan underline decoration-dotted"
      >
        {t('product_detail.refdes_more', { count: refs.length - limit })}
      </button>
    </span>
  );
}
