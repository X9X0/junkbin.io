"""
Parts lists read from the schematics a product already carries, written as
import_board_bom bundles.

    manage.py extract_schematic_boms OUT_DIR [--manufacturer NAME ...] [--slug SLUG ...]
                                     [--limit N] [--all] [--min-confidence high|medium]

For every product with a PDF schematic and no parts list yet (--all: every
product with a schematic), the schematic engine (apps.products.schematic_ocr_utils,
text layer only - scanned pages are left for the per-page OCR button) reads each
designator's label. The rows become OUT_DIR/<slug>/bundle.json:

  - a passive whose label gives its value is a Generic part named by its ratings
    ("CAP 100nF 16V X7R 0402"), with the ratings as specifications;
  - a chip's label (Q, D, U designators only) is kept as its part number when the
    site's catalogue already lists that number (its maker is taken from there, the
    row is confirmed), or when the label is part-number shaped (three digits or
    more, no net-name punctuation): then the maker is the one the number's prefix
    names, else "Generic", and the row is marked unconfirmed for review
    ("part number read from the schematic label; no factory BOM checked it");
  - "low" rows (no value could be read), net names and labels on connectors,
    fuses, jumpers, relays and transformers are left out.

Rows graded high or medium are imported alike: on 1,223 schematics checked against
factory BOMs and boardviews both grades read the value right 96-99% of the time.
The bundle carries add_components_to_existing, so import_board_bom puts the rows on
the product under the tag schematic-bom:<slug> without touching the product's own
import or its documents, and a re-run replaces them.
"""
import json
import logging
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.components.models import Component
from apps.components.spec_parse import guess_maker
from apps.products.schematic_values import VALUE_WORD
from apps.products.models import Product, Schematic
from apps.products.schematic_ocr_utils import build_candidates_from_schematic_file, group_identical

logger = logging.getLogger(__name__)

READABLE = (Schematic.SchematicType.FULL_SCHEMATIC, Schematic.SchematicType.PCB_LAYOUT,
            Schematic.SchematicType.OTHER)
GRADE = {'high': 2, 'medium': 1, 'low': 0}
UNCONFIRMED = 'part number read from the schematic label; no factory BOM checked it'
FLAG_WORDS = ('not fitted', 'fitted in build', 'build option')
CHIP_DESIGNATOR = re.compile(r'^(?:Q|PQ|MQ|TR|U|PU|IC|D|PD|ZD|CR)\d', re.I)
# a part number, not a net name: three digits or more ('2N7002', 'MMBT3904', 'ISL6605B'), none of the
# punctuation nets carry ('P1V2_HT', 'MEMDQS(0)', 'SBD5+', '-BR0')
PART_SHAPED = re.compile(r'^(?=(?:[^0-9]*[0-9]){3})(?=.*[A-Z])[A-Z0-9]{2}[A-Z0-9./-]{2,39}$', re.I)


class Command(BaseCommand):
    help = 'Write parts-list bundles read from the schematics products already carry (import with import_board_bom)'

    def add_arguments(self, parser):
        parser.add_argument('out_dir')
        parser.add_argument('--manufacturer', action='append', default=[], help='Only this maker (repeatable)')
        parser.add_argument('--slug', action='append', default=[], help='Only this product (repeatable)')
        parser.add_argument('--limit', type=int, default=None)
        parser.add_argument('--all', action='store_true', help='Also products that already have a parts list')
        parser.add_argument('--min-confidence', choices=['high', 'medium'], default='medium')

    def handle(self, *args, **options):
        out = Path(options['out_dir'])
        out.mkdir(parents=True, exist_ok=True)
        qs = Product.objects.annotate(n_rows=Count('product_components', distinct=True)).filter(
            schematics__schematic_type__in=READABLE, schematics__file_type='pdf').distinct()
        if options['manufacturer']:
            qs = qs.filter(manufacturer__in=options['manufacturer'])
        if options['slug']:
            qs = qs.filter(slug__in=options['slug'])
        if not options['all']:
            qs = qs.filter(n_rows=0)
        qs = qs.order_by('manufacturer', 'model_number', 'revision')
        if options['limit']:
            qs = qs[:options['limit']]
        floor = GRADE[options['min_confidence']]
        written = skipped = 0
        for product in qs.iterator():
            try:
                bundle = build_bundle(product, floor)
            except Exception as exc:                        # a broken PDF must not stop the sweep
                logger.warning('%s: %s', product.slug, exc)
                self.stderr.write(f'{product.slug}: {exc}')
                skipped += 1
                continue
            if not bundle['components']:
                skipped += 1
                continue
            folder = out / product.slug
            folder.mkdir(exist_ok=True)
            (folder / 'bundle.json').write_text(json.dumps(bundle, indent=1, ensure_ascii=False))
            written += 1
            self.stdout.write(f"{product.slug}: {len(bundle['components'])} parts, "
                              f"{sum(len(c['reference_designators']) for c in bundle['components'])} positions, "
                              f"{bundle['stats']['unconfirmed']} unconfirmed")
        self.stdout.write(self.style.SUCCESS(f'{written} bundles written to {out}, {skipped} products without a readable list'))


def build_bundle(product, floor=GRADE['medium']):
    """The import_board_bom bundle for one product, or one with no components when nothing was read."""
    docs = product.schematics.filter(schematic_type__in=READABLE, file_type='pdf').order_by('uploaded_at')
    best = {}                                                   # designator -> best row across the documents
    titles = []
    for doc in docs:
        titles.append(doc.title or doc.file.name.rsplit('/', 1)[-1])
        with doc.file.open('rb') as fh:
            rows = build_candidates_from_schematic_file(fh, 'pdf', ocr=False)
        for row in rows:
            ref = row['reference_designator'].upper()
            if GRADE.get(row['confidence'], 0) < floor or not row.get('part_number'):
                continue
            if ref not in best or GRADE[row['confidence']] > GRADE[best[ref]['confidence']]:
                best[ref] = row
    rows = [r for r in best.values() if usable(r)]
    grouped = group_identical(sorted(rows, key=lambda r: (r['page_number'], r['reference_designator'])))
    known = catalogue_makers(g['part_number'] for g in grouped if g['manufacturer'] != 'Generic')
    merged = {}                                 # the engine groups Generic rows; chips are grouped here
    for g in grouped:
        entry = component_entry(g, known)
        key = (entry['part_number'].upper(), entry['manufacturer'], entry['component_type'], entry['package_type'],
               entry.get('unconfirmed', ''), tuple(f for f in entry['notes'].split('; ') if f.startswith(FLAG_WORDS)))
        if key in merged:
            merged[key]['reference_designators'] += entry['reference_designators']
            merged[key]['quantity'] = len(merged[key]['reference_designators'])
        else:
            merged[key] = entry
    components = list(merged.values())
    unconfirmed = sum(1 for c in components if c.get('unconfirmed'))
    graded = {k: sum(1 for r in rows if r['confidence'] == k) for k in ('high', 'medium')}
    return {
        'bundle_version': 1,
        'source_tag': f'schematic-bom:{product.slug}',
        'source_note': (f"Parts list read from the schematic text layer by the site's schematic engine: "
                        f"{'; '.join(titles)}. {len(rows)} positions read ({graded['high']} high, "
                        f"{graded['medium']} medium confidence); chips are marked for review until a factory BOM "
                        f"or distributor listing confirms them."),
        'product': {'manufacturer': product.manufacturer, 'model_number': product.model_number,
                    'revision': product.revision, 'category': product.category,
                    'subcategory': product.subcategory, 'year_manufactured': product.year_manufactured,
                    'description': product.description},
        'add_components_to_existing': True,
        'components': components,
        'stats': {'positions': len(rows), 'parts': len(components), 'unconfirmed': unconfirmed, **graded},
    }


def usable(row):
    """A row the list can carry: a Generic passive with a plausible value, or a chip with a
    part-number-shaped label."""
    if row['manufacturer'] == 'Generic':
        return bool(row.get('specifications')) and plausible(row['specifications'])
    pn = (row['part_number'] or '').strip()
    if VALUE_WORD.match(pn):
        return False                    # '470Ohm' at D8: a neighbour's value, not a diode's part number
    return bool(row['manufacturer'] or (CHIP_DESIGNATOR.match(row['reference_designator']) and PART_SHAPED.match(pn)))


VALUE_KEYS = ('resistance_ohm', 'capacitance_pf', 'inductance_uh')


def plausible(specs):
    """False when a passive's value has more than three significant digits: no E-series value
    does (E192 stops at three), so '1005' (a metric size code), '25201' (a designator number)
    or '10024' (a net name) read as ohms is a misread, not a part."""
    for key in VALUE_KEYS:
        v = specs.get(key)
        if isinstance(v, (int, float)) and v > 0:
            digits = f'{v:.10g}'.replace('.', '').replace('e', 'X').split('X')[0].strip('0')
            if len(digits) > 3:
                return False
    return True


def catalogue_makers(part_numbers):
    """part number (upper) -> maker for the numbers the catalogue already lists, the most-used maker
    first; a number the catalogue only knows as Generic is confirmed as Generic."""
    wanted = {pn.strip().upper() for pn in part_numbers if pn}
    known = {}
    for maker, pn, used in (Component.objects.filter(part_number__in=wanted).order_by('-usage_count')
                            .values_list('manufacturer', 'part_number', 'usage_count')):
        key = pn.upper()
        if key not in known or (known[key] == 'Generic' and maker != 'Generic'):
            known[key] = maker
    return known


def component_entry(g, known=None):
    refs = [r.strip() for r in g['reference_designator'].split(',') if r.strip()]
    flags = [f for f in g['description'].split('; ') if f.startswith(FLAG_WORDS)]
    label = g.get('value_raw') or ''
    notes = '; '.join(x for x in (f"schematic label '{label}'" if label else '', *flags) if x)
    if g['manufacturer'] == 'Generic':
        return {
            'part_number': g['part_number'], 'manufacturer': 'Generic',
            'component_type': g['component_type'] or '', 'package_type': g['package_type'] or '',
            'description': g['part_number'], 'specifications': g.get('specifications') or {},
            'reference_designators': refs, 'quantity': len(refs), 'notes': notes,
        }
    pn = g['part_number'].strip()
    listed = (known or {}).get(pn.upper())
    maker = g['manufacturer'] or listed or guess_maker(pn) or 'Generic'
    return {
        'part_number': pn, 'manufacturer': maker,
        'component_type': g['component_type'] or '', 'package_type': g['package_type'] or '',
        'description': f'{pn} ({g["component_type"]})' if g['component_type'] else pn,
        'specifications': {}, 'reference_designators': refs, 'quantity': len(refs), 'notes': notes,
        'unconfirmed': UNCONFIRMED if not (g['manufacturer'] or listed) else '',
    }
