// Component ratings as the API sends them (Component.ratings on the backend):
// display text plus a number in base units for sorting.
export interface Rating {
  text: string;
  sort: number | null;
}

export type RatingKey =
  | 'value' | 'voltage' | 'power' | 'current' | 'tolerance' | 'dielectric' | 'load' | 'configuration';

export type Ratings = Partial<Record<RatingKey, Rating>>;

// Column order in BOM tables and rows in the specifications table
export const RATING_COLUMNS: RatingKey[] = [
  'value', 'voltage', 'power', 'current', 'tolerance', 'dielectric', 'load', 'configuration',
];

interface HasComponent {
  reference_designator?: string;
  quantity?: number;
  component: {
    part_number: string;
    manufacturer: string;
    component_type: string;
    component_type_display?: string;
    package_type?: string;
    primary_value?: string;
    ratings?: Ratings;
  };
}

/** Rating columns that at least one row of this BOM has (Value is always shown). */
export function visibleRatingColumns(rows: HasComponent[] | undefined): RatingKey[] {
  if (!rows) return ['value'];
  return RATING_COLUMNS.filter((key) => key === 'value' || rows.some((r) => r.component.ratings?.[key]));
}

export function hasPackageColumn(rows: HasComponent[] | undefined): boolean {
  return !!rows?.some((r) => r.component.package_type);
}

export function ratingText(row: HasComponent, key: RatingKey): string {
  if (key === 'value') return row.component.ratings?.value?.text || row.component.primary_value || '';
  return row.component.ratings?.[key]?.text || '';
}

/** 'C12' < 'C102' < 'R3': letters first, then the number. */
function compareRefdes(a = '', b = ''): number {
  const pa = /^([A-Za-z]*)(\d*)/.exec(a.split(',')[0].trim()) ?? ['', '', ''];
  const pb = /^([A-Za-z]*)(\d*)/.exec(b.split(',')[0].trim()) ?? ['', '', ''];
  return pa[1].localeCompare(pb[1]) || (Number(pa[2] || 0) - Number(pb[2] || 0)) || a.localeCompare(b);
}

export type BomSortKey = RatingKey | 'ref' | 'part' | 'manufacturer' | 'type' | 'qty' | 'package';

/** Sorted copy of the BOM; rows without the sorted value always go last. */
export function sortBom<T extends HasComponent>(rows: T[], key: BomSortKey, dir: 1 | -1): T[] {
  const value = (r: T): string | number | null => {
    const c = r.component;
    switch (key) {
      case 'ref': return r.reference_designator || null;
      case 'part': return c.part_number;
      case 'manufacturer': return c.manufacturer;
      case 'type': return c.component_type_display || c.component_type;
      case 'qty': return r.quantity ?? null;
      case 'package': return c.package_type || null;
      default: {
        const rating = c.ratings?.[key];
        if (!rating) return key === 'value' && c.primary_value ? c.primary_value : null;
        return rating.sort ?? rating.text;
      }
    }
  };
  return [...rows].sort((a, b) => {
    const va = value(a);
    const vb = value(b);
    if (va === null || va === '') return vb === null || vb === '' ? 0 : 1;
    if (vb === null || vb === '') return -1;
    if (key === 'ref') return dir * compareRefdes(String(va), String(vb));
    if (typeof va === 'number' && typeof vb === 'number') return dir * (va - vb);
    if (typeof va === 'number') return -1;                // numbers before free text
    if (typeof vb === 'number') return 1;
    return dir * String(va).localeCompare(String(vb), undefined, { numeric: true });
  });
}
