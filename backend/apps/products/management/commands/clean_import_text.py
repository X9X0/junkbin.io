"""
Apply apps.products.import_text cleaning to bulk-imported content already in
the database (glossary translation of factory shorthand, advert/download-site
removal, datasheet descriptions rebuilt from their English title text).

    manage.py clean_import_text [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.components.models import Component, ComponentDatasheet, ProductComponent
from apps.products.import_text import bom_component_type, clean_description, clean_text, clean_title
from apps.products.models import Product, Schematic


class Command(BaseCommand):
    help = 'Clean text of bulk-imported products, BOM rows, components, documents and datasheets'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        counts = {}
        with transaction.atomic():
            counts['bom notes'] = self.fix(ProductComponent.objects.exclude(import_source=''), 'notes', clean_text)
            counts['document titles'] = self.fix(Schematic.objects.filter(source_notes__startswith='[norway-'),
                                                 'title', clean_title)
            counts['datasheet titles'] = self.fix(ComponentDatasheet.objects.filter(source_notes__startswith='[norway-'),
                                                  'title', clean_title)
            counts['datasheet-made component descriptions'] = self.fix(
                Component.objects.filter(specifications__source='datasheet'), 'description', clean_description)
            counts['imported component descriptions'] = self.fix(
                Component.objects.filter(product_components__import_source__gt='').distinct(), 'description', clean_text)
            counts['product descriptions'] = self.fix(Product.objects.exclude(import_source=''),
                                                     'description', clean_text)
            counts['alternate descriptions'] = self.fix_alternates()
            counts['component types'] = self.fix_types()
            if options['dry_run']:
                transaction.set_rollback(True)
        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(prefix + ', '.join(f'{k}: {v} changed' for k, v in counts.items())))

    @staticmethod
    def fix(queryset, field, cleaner):
        """Clean `field` on every row of `queryset`; returns how many rows changed."""
        model, batch, total = queryset.model, [], 0
        for obj in queryset.only('pk', field).iterator():
            before = getattr(obj, field) or ''
            after = cleaner(before)
            if after != before:
                setattr(obj, field, after)
                batch.append(obj)
                total += 1
            if len(batch) >= 1000:
                model.objects.bulk_update(batch, [field])
                batch = []
        if batch:
            model.objects.bulk_update(batch, [field])
        return total

    @staticmethod
    def fix_alternates():
        """Second-source components created by BOM imports were given their primary's BOM line as
        description, which names a different part number. Describe them as alternates instead."""
        from apps.products.management.commands.import_board_bom import alternate_description
        total = 0
        alternates = (Component.objects.filter(product_components__isnull=True,
                                               cross_references__product_components__import_source__gt='')
                      .distinct())
        for alt in alternates:
            desc = alt.description or ''
            if alt.part_number.upper() in desc.upper() and not desc.startswith('Factory-approved alternate'):
                continue                       # its description is about itself - leave it
            primaries = list(alt.cross_references.filter(product_components__import_source__gt='')
                             .distinct().order_by('manufacturer', 'part_number'))
            if desc.startswith('Factory-approved alternate') and any(
                    f'{p.manufacturer} {p.part_number}' in desc for p in primaries):
                continue                       # already names one of its primaries
            primary = primaries[0]
            new = alternate_description({'manufacturer': primary.manufacturer, 'part_number': primary.part_number,
                                         'description': primary.description,
                                         'component_type': primary.component_type})
            if new != alt.description:
                alt.description = new
                alt.save(update_fields=['description'])
                total += 1
        return total

    @staticmethod
    def fix_types():
        """BOM-imported components typed 'ic'/'other' by default whose factory line says what they are."""
        total = 0
        qs = (Component.objects.filter(component_type__in=['ic', 'other'],
                                       product_components__import_source__startswith='norway-bom').distinct())
        for comp in qs:
            line = comp.product_components.filter(import_source__startswith='norway-bom').values_list(
                'notes', flat=True).first() or ''
            line = line.replace('Factory BOM line:', '').split(';')[0].strip() or comp.description
            kind = bom_component_type(line) or bom_component_type(comp.description)
            if kind and kind != comp.component_type:
                comp.component_type = kind
                comp.save(update_fields=['component_type'])
                total += 1
        return total
