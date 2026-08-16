"""
Reconcile Component.part_number against a product's uploaded PDF service
manual's "Electrical Replacement Parts List" table.

Some bulk-imported BOMs land with the manual's *internal* service reference
code as Component.part_number (e.g. Panasonic's internal code
"C0JBAA000014") instead of the actual manufacturer part number (e.g.
"NJM4565MD") - the PDF's own replacement parts list has both, in a
"Ref.No. | Part No. | Part Name & Description | Pcs | Remarks" table where
Ref.No. is the schematic reference designator and Remarks holds the
internal code.

pdf_bom_utils' structured table extraction doesn't recognize "Ref.No." as
a reference-designator column header (fixed separately in bom_utils.py),
so this re-parses the raw extraction_context text directly instead of
relying on the (currently blank) structured reference_designator field.

Only touches a component when BOTH its reference designator and its
*current* part_number match a row in that table exactly - that internal
code is the safety anchor confirming this is really the same part, not a
guess based on position or fuzzy matching. Anything ambiguous (no match,
multiple components sharing a reference designator, or a part_number that
doesn't match the anchor) is left alone.
"""
import re

from django.core.management.base import BaseCommand, CommandError

from apps.components.models import Component, ProductComponent
from apps.products.models import Schematic
from apps.products.pdf_bom_utils import build_candidates_from_pdf

ROW_PATTERN = re.compile(
    r'Ref\.No\.:\s*(?P<ref>\S+)\s*\|\s*Part No\.:\s*(?P<pn>\S+)\s*\|'
    r'\s*Part Name & Description:\s*(?P<name>.*?)\s*\|\s*Pcs:\s*(?P<pcs>\d+)'
    r'(?:\s*\|\s*Remarks:\s*(?P<remarks>\S+))?\s*$'
)


class Command(BaseCommand):
    help = (
        "Reconcile Component.part_number against a product's PDF service "
        "manual replacement parts list (Ref.No./Part No./Remarks table)."
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
        product_id = options['product']

        schematic = (
            Schematic.objects
            .filter(product_id=product_id, file_type='pdf', is_approved=True)
            .exclude(file='')
            .first()
        )
        if not schematic:
            raise CommandError('No approved PDF schematic found for this product.')

        candidates = build_candidates_from_pdf(schematic.file)
        rows = []
        for candidate in candidates:
            match = ROW_PATTERN.search(candidate.get('extraction_context', ''))
            if match:
                rows.append(match.groupdict())
        self.stdout.write(f'Parsed {len(rows)} replacement-parts-list rows from the PDF.')

        by_ref = {}
        product_components = (
            ProductComponent.objects
            .filter(product_id=product_id)
            .select_related('component')
        )
        for pc in product_components:
            by_ref.setdefault(pc.reference_designator, []).append(pc)

        renamed = 0
        reassigned = 0
        already_correct = 0
        no_unambiguous_match = 0
        anchor_mismatch = 0

        for row in rows:
            internal_code = row['remarks']
            if not internal_code:
                continue  # no internal code to cross-validate against - too risky to touch

            matches = by_ref.get(row['ref'])
            if not matches or len(matches) != 1:
                no_unambiguous_match += 1
                continue

            pc = matches[0]
            component = pc.component
            real_part_number = row['pn']

            if component.part_number == real_part_number:
                already_correct += 1
                continue
            if component.part_number != internal_code:
                # Doesn't match the safety anchor - could already be a
                # different, unrelated part. Don't touch it.
                anchor_mismatch += 1
                continue

            self.stdout.write(f'{row["ref"]}: {component.part_number} -> {real_part_number}')
            if dry_run:
                continue

            existing = (
                Component.objects
                .filter(manufacturer=component.manufacturer, part_number=real_part_number)
                .exclude(pk=component.pk)
                .first()
            )
            if existing:
                pc.component = existing
                pc.save(update_fields=['component'])
                component.update_usage_count()
                existing.update_usage_count()
                reassigned += 1
            else:
                component.part_number = real_part_number
                component.save(update_fields=['part_number'])
                renamed += 1

        self.stdout.write(self.style.SUCCESS(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'{renamed} renamed in place, {reassigned} reassigned to an existing canonical component, '
            f'{already_correct} already correct, {no_unambiguous_match} had no unambiguous BOM match, '
            f'{anchor_mismatch} failed the internal-code safety check (skipped).'
        ))
