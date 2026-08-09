"""
Management command to back-fill ComponentSuggestions from already-uploaded
PDF schematics/service manuals.

Run this once to sweep the existing library after the PDF BOM-extraction
feature shipped - going forward, uploaders can also trigger extraction
per-schematic from the product page. Every processed schematic gets
bom_extracted_at stamped so re-running the sweep skips it, unless
--reprocess is passed.

Only considers schematic_type values in Schematic.BOM_EXTRACTABLE_TYPES
(Service Manual, Bill of Materials) - circuit diagrams don't have text/
table BOM data this extractor can find.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.products.models import Schematic, ComponentSuggestion
from apps.products.pdf_bom_utils import build_candidates_from_pdf, find_component_match


class Command(BaseCommand):
    help = 'Extract candidate BOM rows from existing PDF schematics/manuals and queue them for moderator review.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            help='Only process schematics belonging to this product UUID.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Stop after processing this many schematics.',
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Also process schematics that already have bom_extracted_at set.',
        )
        parser.add_argument(
            '--min-confidence',
            choices=['high', 'low'],
            default='high',
            help=(
                "Minimum confidence to actually queue as a suggestion (default: high, "
                "i.e. table-extracted rows only). The heuristic 'low' text-scan pass is "
                "noisier on real-world manuals - pass --min-confidence low to include it "
                "for a single product you plan to review closely, not for a full sweep."
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would happen without creating suggestions or stamping bom_extracted_at.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        schematics = Schematic.objects.filter(
            is_approved=True,
            file_type='pdf',
            schematic_type__in=Schematic.BOM_EXTRACTABLE_TYPES,
        ).select_related('product', 'uploaded_by')

        if not options['reprocess']:
            schematics = schematics.filter(bom_extracted_at__isnull=True)

        if options['product']:
            schematics = schematics.filter(product_id=options['product'])

        if options['limit']:
            schematics = schematics[:options['limit']]

        min_confidence = options['min_confidence']
        allowed_confidences = {'high'} if min_confidence == 'high' else {'high', 'low'}

        total_schematics = 0
        total_candidates = 0
        total_queued = 0
        total_created = 0
        failed = 0

        for schematic in schematics:
            total_schematics += 1
            label = f'{schematic.product} - {schematic.title}'

            try:
                candidates = build_candidates_from_pdf(schematic.file)
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f'{label}: {exc}'))
                continue

            total_candidates += len(candidates)
            queued = [c for c in candidates if c['confidence'] in allowed_confidences]
            total_queued += len(queued)
            self.stdout.write(
                f'{label}: {len(candidates)} candidate(s) found, {len(queued)} at/above --min-confidence'
            )

            if dry_run:
                continue

            for candidate in queued:
                part_number = str(candidate.get('part_number', '')).strip()
                if not part_number:
                    continue
                manufacturer = str(candidate.get('manufacturer', '')).strip()
                match = find_component_match(part_number, manufacturer)

                ComponentSuggestion.objects.create(
                    product=schematic.product,
                    source_type=ComponentSuggestion.SourceType.PDF_MANUAL,
                    page_number=candidate.get('page_number') or None,
                    extraction_context=str(candidate.get('extraction_context', ''))[:2000],
                    confidence=candidate.get('confidence') or ComponentSuggestion.Confidence.MEDIUM,
                    part_number=part_number,
                    manufacturer=manufacturer,
                    reference_designator=str(candidate.get('reference_designator', '')).strip(),
                    component_type=str(candidate.get('component_type', '')).strip(),
                    package_type=str(candidate.get('package_type', '')).strip(),
                    description=str(candidate.get('description', ''))[:500],
                    value_raw=str(candidate.get('value_raw', '')).strip(),
                    quantity=max(1, int(candidate.get('quantity', 1) or 1)),
                    location_description=str(candidate.get('location_description', '')).strip(),
                    matched_component=match,
                    uploaded_by=schematic.uploaded_by,
                )
                total_created += 1

            Schematic.objects.filter(pk=schematic.pk).update(bom_extracted_at=timezone.now())

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] {total_schematics} schematic(s) scanned, '
                f'{total_candidates} candidate(s) found ({total_queued} at/above --min-confidence={min_confidence}), '
                f'{failed} failed. Nothing was saved.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{total_schematics} schematic(s) scanned, {total_created} component '
                f'suggestion(s) created, {failed} failed.'
            ))
