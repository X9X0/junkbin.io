// Chip package sizes in both systems: EIA names a chip in hundredths of an inch (0603 = 0.06 x 0.03 in), IEC/JIS in
// tenths of a millimetre (1608 = 1.6 x 0.8 mm). The site stores the EIA code; the metric twin is shown beside it so a
// reader used to either system recognises the size. Mirrors backend apps/components/packages.py.
const EIA_TO_METRIC: Record<string, string> = {
  '01005': '0402', '0201': '0603', '0402': '1005', '0603': '1608', '0805': '2012', '1008': '2520',
  '1206': '3216', '1210': '3225', '1806': '4516', '1812': '4532', '2010': '5025', '2512': '6332',
};
const CHIP_CODE = /(?<![\dA-Z])(01005|0201|0402|0603|0805|1008|1206|1210|1806|1812|2010|2512)(?!\d)/;

/** The IEC/JIS metric code for a package stored by its EIA code, or '' when it is not a chip size. */
export function metricFor(packageType?: string | null): string {
  const m = (packageType || '').match(CHIP_CODE);
  return m ? EIA_TO_METRIC[m[1]] || '' : '';
}

/** '0603 EIA · 1608 metric' for a chip size, the package as stored otherwise. */
export function formatPackage(packageType?: string | null, metric?: string | null): string {
  const pkg = (packageType || '').trim();
  if (!pkg) return '';
  const twin = metric ?? metricFor(pkg);
  return twin ? `${pkg} EIA · ${twin} metric` : pkg;
}
