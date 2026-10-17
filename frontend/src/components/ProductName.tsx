import { useTranslation } from 'react-i18next';

interface Named {
  model_number: string;
  revision?: string | null;
}

/**
 * Model name as one line of text, with the revision when there is one:
 * "WMTA (Rev: 1.05)". For alt text, breadcrumbs, dialogs and compact lists.
 */
export function productNameText(product: Named, revisionLabel: string): string {
  const revision = product.revision?.trim();
  return revision ? `${product.model_number} (${revisionLabel} ${revision})` : product.model_number;
}

/**
 * Model name for titles and cards. Revisions of one model are separate
 * products, so the revision sits on the title line where it can't be missed;
 * a long model name truncates, the revision badge never does.
 */
export default function ProductName({ product, className = '' }: { product: Named; className?: string }) {
  const { t } = useTranslation();
  const revision = product.revision?.trim();
  return (
    <span className={`flex items-baseline gap-2 min-w-0 ${className}`}>
      <span className="truncate">{product.model_number}</span>
      {revision && (
        <span className="flex-shrink-0 font-mono text-xs font-normal text-cyber-cyan">
          {t('products.revision')} {revision}
        </span>
      )}
    </span>
  );
}
