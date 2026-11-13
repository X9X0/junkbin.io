"""
Tidy the Generic parts whose names are a bare value where a part number belongs.

Two kinds of row, both found 2026-11-12 while checking the catalogue's naming:

1. Misreads from the schematic extractor: a value next to a chip designator kept as the
   chip's part number ("470Ohm" as a transistor at Q6202, "15V" as a diode at D9,
   "400MHz" as an IC at U47). The extractor no longer writes them (VALUE_WORD in
   schematic_values); the rows it already wrote are removed here: every placement under a
   `schematic-bom:` tag whose component is Generic, chip-typed and value-named, then the
   component itself once nothing uses it. Hand-written lists (schematicheaven, amiga-docs)
   are left alone - a "15V" diode in an amp list is a repairer's shorthand for a zener.

2. Names spelled against the engine's convention that mean the same as an existing part:
   MERGES moves their placements onto the conventional part and deletes them.

    python manage.py tidy_generic_names --dry-run
    python manage.py tidy_generic_names
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.components.models import Component, ProductComponent
from apps.products.management.commands.import_board_bom import refresh_usage_counts
from apps.products.models import Product
from apps.products.schematic_values import VALUE_WORD

CHIP_TYPES = ('transistor', 'diode', 'ic')
MISREAD_TAG = 'schematic-bom:'
# off-convention name -> the engine's name for the same part (both Generic)
MERGES = {'32.768 kHz crystal': 'XTAL 32.768kHz'}


def value_named_chips():
    return [c for c in Component.objects.filter(manufacturer='Generic', component_type__in=CHIP_TYPES)
            if VALUE_WORD.match(c.part_number.strip())]


class Command(BaseCommand):
    help = 'Remove value-named chip misreads from schematic lists and merge off-convention Generic names'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='report what would change; write nothing')

    def handle(self, *args, **options):
        dry = options['dry_run']
        touched_products, touched_components = set(), set()
        with transaction.atomic():
            chips = value_named_chips()
            rows = ProductComponent.objects.filter(component__in=chips, import_source__startswith=MISREAD_TAG)
            placements = rows.count()
            touched_products |= set(rows.values_list('product_id', flat=True))
            touched_components |= {c.pk for c in chips}
            for c in chips:
                n = rows.filter(component=c).count()
                if n:
                    self.stdout.write(f'misread {c.part_number!r} ({c.component_type}): {n} placement(s) removed')
            rows.delete()
            orphans = Component.objects.filter(pk__in=[c.pk for c in chips]).annotate(n=Count('product_components')).filter(n=0)
            orphan_names = sorted(orphans.values_list('part_number', flat=True))
            removed_components = orphans.count()
            orphans.delete()

            merged = 0
            for old_name, new_name in MERGES.items():
                old = Component.objects.filter(manufacturer='Generic', part_number=old_name).first()
                new = Component.objects.filter(manufacturer='Generic', part_number=new_name).first()
                if not old or not new:
                    continue
                moved = ProductComponent.objects.filter(component=old)
                touched_products |= set(moved.values_list('product_id', flat=True))
                touched_components |= {old.pk, new.pk}
                merged += moved.update(component=new)
                self.stdout.write(f'merged {old_name!r} into {new_name!r}: {merged} placement(s)')
                old.delete()

            refresh_usage_counts(touched_components)
            for product in Product.objects.filter(pk__in=touched_products):
                product.update_component_count()

            summary = (f'{"DRY RUN (rolled back) - " if dry else ""}misread placements removed {placements}, '
                       f'components removed {removed_components} ({", ".join(orphan_names)}), placements merged {merged}, '
                       f'products recounted {len(touched_products)}')
            self.stdout.write(summary)
            if dry:
                transaction.set_rollback(True)
