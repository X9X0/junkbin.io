"""
Backfill Component.specifications and Component.description from the raw
BOM text on ProductComponent.

Bulk-imported BOMs (e.g. scanned/OCR'd from a service manual) often land
with everything only present in the freeform notes column, e.g.
"5% CERAMIC CHIP 470PF | 50V" - Component.specifications and .description
stay empty, so primary_value/description have nothing to show on the
product page even though a schematic/manual is right there listing it.

Only touches resistor/capacitor/inductor components (the types
value_parsing.py knows how to read) and only fills fields that are still
unset, so it never overwrites something someone already verified.
"""
from django.core.management.base import BaseCommand

from apps.components.models import ProductComponent
from apps.components.value_parsing import PARSERS, parse_description


class Command(BaseCommand):
    help = (
        'Parse resistor/capacitor/inductor values and descriptions out of '
        'ProductComponent.notes and store them on the linked Component.'
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

        value_updated = value_already_set = 0
        description_updated = description_already_set = description_skipped = 0
        value_unparsed = []
        seen_component_ids = set()

        for pc in product_components:
            component = pc.component
            if component.id in seen_component_ids:
                continue
            seen_component_ids.add(component.id)

            update_fields = []

            spec_key, parse_value = PARSERS[component.component_type]
            specs = component.specifications or {}
            if specs.get(spec_key) is not None:
                value_already_set += 1
            else:
                value = parse_value(pc.notes)
                if value is None:
                    value_unparsed.append((pc.reference_designator, component.component_type, pc.notes))
                else:
                    specs[spec_key] = value
                    component.specifications = specs
                    update_fields.append('specifications')
                    value_updated += 1
                    if dry_run:
                        self.stdout.write(f'{pc.reference_designator} ({component.part_number}): {spec_key} = {value!r}')

            if component.description:
                description_already_set += 1
            else:
                description = parse_description(component.component_type, pc.notes)
                if description is None:
                    description_skipped += 1
                else:
                    component.description = description
                    update_fields.append('description')
                    description_updated += 1
                    if dry_run:
                        self.stdout.write(f'{pc.reference_designator} ({component.part_number}): description = {description!r}')

            if update_fields and not dry_run:
                component.save(update_fields=update_fields)

        self.stdout.write(self.style.SUCCESS(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'Values: {value_updated} updated, {value_already_set} already set, {len(value_unparsed)} unparsed.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Descriptions: {description_updated} updated, {description_already_set} already set, '
            f'{description_skipped} left blank (construction type not recognized).'
        ))
        if value_unparsed:
            self.stdout.write('Values left for manual review:')
            for ref, ctype, notes in value_unparsed:
                self.stdout.write(f'  {ref} ({ctype}): {notes!r}')
