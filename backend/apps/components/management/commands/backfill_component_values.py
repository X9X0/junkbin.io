"""
Backfill Component.specifications from the raw BOM text on ProductComponent.

Bulk-imported BOMs (e.g. scanned/OCR'd from a service manual) often land
with the value only present in the freeform notes column, e.g.
"5% CERAMIC CHIP 470PF | 50V" - Component.specifications stays empty, so
primary_value has nothing to show on the product page even though a
schematic/manual is right there listing the value.

Only touches resistor/capacitor/inductor components (the types
value_parsing.py knows how to read) and only fills specifications keys that
are still unset, so it never overwrites a value someone already verified.
"""
from django.core.management.base import BaseCommand

from apps.components.models import ProductComponent
from apps.components.value_parsing import PARSERS


class Command(BaseCommand):
    help = (
        'Parse resistor/capacitor/inductor values out of ProductComponent.notes '
        'and store them in Component.specifications so primary_value has something to show.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            required=True,
            help='Only process components belonging to this product UUID.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without saving anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        product_components = ProductComponent.objects.filter(
            product_id=options['product'],
            component__component_type__in=PARSERS.keys(),
        ).select_related('component')

        updated = 0
        already_set = 0
        unparsed = []
        seen_component_ids = set()

        for pc in product_components:
            component = pc.component
            if component.id in seen_component_ids:
                continue
            seen_component_ids.add(component.id)

            spec_key, parse = PARSERS[component.component_type]
            specs = component.specifications or {}

            if specs.get(spec_key) is not None:
                already_set += 1
                continue

            value = parse(pc.notes)
            if value is None:
                unparsed.append((pc.reference_designator, component.component_type, pc.notes))
                continue

            specs[spec_key] = value
            updated += 1
            if dry_run:
                self.stdout.write(f'{pc.reference_designator} ({component.part_number}): {spec_key} = {value!r}')
            else:
                component.specifications = specs
                component.save(update_fields=['specifications'])

        self.stdout.write(self.style.SUCCESS(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'{updated} component(s) updated, {already_set} already had a value, '
            f'{len(unparsed)} could not be parsed.'
        ))
        if unparsed:
            self.stdout.write('Unparsed (left for manual review):')
            for ref, ctype, notes in unparsed:
                self.stdout.write(f'  {ref} ({ctype}): {notes!r}')
