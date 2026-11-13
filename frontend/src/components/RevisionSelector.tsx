import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ChevronDown, GitBranch } from 'lucide-react';
import type { Product } from '../types';

/**
 * One product page per hardware revision, one selector over all of them. Revisions of a
 * model are separate products (MSI MS-9902 rev 0A, 0B, 1.0, 1.1 ...), each with its own
 * parts list and drawings; the backend lists the siblings in `product.revisions`, so a
 * repairer who landed on the wrong revision can switch without searching again. The option
 * text carries the part and schematic counts, which is how one tells the revision that
 * actually has the list from the ones that only hold a drawing.
 */
export default function RevisionSelector({ product }: { product: Product }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const revisions = product.revisions ?? [];
  if (revisions.length < 2) return null;

  const current = revisions.find((r) => r.id === product.id)?.id ?? '';
  const manyRegions = new Set(revisions.map((r) => r.region)).size > 1;
  const label = (r: (typeof revisions)[number]) => {
    const name = r.revision ? `${t('products.revision')} ${r.revision}` : t('product_detail.revision_unspecified');
    const region = manyRegions ? ` · ${r.region_display}` : '';
    return `${name}${region} · ${t('product_detail.revision_summary', { parts: r.component_count, schematics: r.schematic_count })}`;
  };

  return (
    <div className="mt-3">
      <label className="flex items-center gap-1.5 text-xs font-mono text-gray-500 mb-1" htmlFor="revision-selector">
        <GitBranch className="h-3.5 w-3.5" />
        {t('product_detail.revisions_label', { count: revisions.length })}
      </label>
      <div className="relative inline-block w-full sm:w-auto">
        <select
          id="revision-selector"
          value={current}
          onChange={(e) => {
            const target = revisions.find((r) => r.id === e.target.value);
            // product pages are addressed by id: the API has no slug route (slugs are for export files)
            if (target && target.id !== product.id) navigate(`/products/${target.id}`);
          }}
          className="input-cyber appearance-none pr-10 w-full sm:min-w-[22rem] text-sm"
        >
          {revisions.map((r) => (
            <option key={r.id} value={r.id}>
              {label(r)}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
      </div>
    </div>
  );
}
