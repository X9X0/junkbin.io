"""
Apply apps.products.import_text cleaning to bulk-imported content already in
the database (glossary translation of factory shorthand and of the phrases in
apps.products.import_glossary, advert/download-site removal, datasheet descriptions
rebuilt from their English title text): BOM rows, components, products, documents,
firmware files and image captions.

    manage.py clean_import_text [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.components.models import Component, ComponentDatasheet, ProductComponent
from apps.products.import_text import bom_component_type, clean_description, clean_text, clean_title
from apps.products.models import Firmware, Product, ProductImage, Schematic


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
            counts['document descriptions'] = self.fix(Schematic.objects.filter(source_notes__startswith='[norway-'),
                                                       'description', clean_text)
            counts['firmware titles'] = self.fix(Firmware.objects.filter(source_notes__startswith='[norway-'),
                                                 'title', clean_title)
            counts['firmware descriptions'] = self.fix(Firmware.objects.filter(source_notes__startswith='[norway-'),
                                                       'description', clean_text)
            counts['image captions'] = self.fix(
                ProductImage.objects.filter(Q(source_notes__startswith='[') | Q(caption__startswith='First page of'),
                                            product__import_source__startswith='norway-'),
                'caption', lambda c: clean_title(c)[:200])
            counts['datasheet titles'] = self.fix(ComponentDatasheet.objects.filter(source_notes__startswith='[norway-'),
                                                  'title', clean_title)
            counts['datasheet-made component descriptions'] = self.fix_datasheet_descriptions()
            counts['imported component descriptions'] = self.fix(
                Component.objects.filter(product_components__import_source__gt='').distinct(), 'description', clean_text)
            counts['product descriptions'] = self.fix(Product.objects.exclude(import_source=''),
                                                     'description', clean_text)
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
    def fix_datasheet_descriptions():
        """Components made from a datasheet: its title, without banners and the Features column."""
        batch, total = [], 0
        for comp in Component.objects.filter(specifications__source='datasheet').only('pk', 'part_number', 'description'):
            new = clean_description(comp.description, part_number=comp.part_number)
            if new != comp.description:
                comp.description = new
                batch.append(comp)
                total += 1
        Component.objects.bulk_update(batch, ['description'], batch_size=500)
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
            line = line.split('Factory BOM line:')[-1].split(';')[0].strip() or comp.description
            kind = bom_component_type(line) or bom_component_type(comp.description)
            if kind and kind != comp.component_type:
                comp.component_type = kind
                comp.save(update_fields=['component_type'])
                total += 1
        return total
