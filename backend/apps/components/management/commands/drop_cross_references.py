"""
Remove cross-references (equivalent parts) that an import created by mistake.

    manage.py drop_cross_references PAIRS.json [--dry-run]

PAIRS.json is a list of [[manufacturer, part_number], [manufacturer, part_number]]
pairs, matched case-insensitively. The Norway BOM export used to group a line's
factory alternates by item number, which some BOMs reuse, so unrelated lines'
alternates were cross-referenced with each other (a 49.9k resistor "equivalent"
to a 1uF capacitor). The list is the old bundles' pairs minus the corrected
bundles' pairs; a pair the corrected bundles still make is never in it.
"""
import json

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.components.models import Component
from utils.cache import clear_page_cache


class Command(BaseCommand):
    help = 'Remove listed cross-references between components'

    def add_arguments(self, parser):
        parser.add_argument('pairs')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        with open(options['pairs'], encoding='utf-8') as fh:
            pairs = json.load(fh)
        ids = {(m.upper(), p.upper()): pk
               for pk, m, p in Component.objects.values_list('pk', 'manufacturer', 'part_number')}
        through = Component.cross_references.through
        found, missing, removed = 0, 0, 0
        with transaction.atomic():
            batch = Q(pk__in=[])
            for n, (a, b) in enumerate(pairs, 1):
                ia, ib = ids.get((a[0].upper(), a[1].upper())), ids.get((b[0].upper(), b[1].upper()))
                if not ia or not ib:
                    missing += 1
                    continue
                found += 1
                batch |= Q(from_component_id=ia, to_component_id=ib) | Q(from_component_id=ib, to_component_id=ia)
                if n % 500 == 0:
                    removed += through.objects.filter(batch).delete()[0]
                    batch = Q(pk__in=[])
            removed += through.objects.filter(batch).delete()[0]
            touched = Component.objects.filter(pk__in={i for pair in pairs for i in (
                ids.get((pair[0][0].upper(), pair[0][1].upper())), ids.get((pair[1][0].upper(), pair[1][1].upper())))
                if i})
            if options['dry_run']:
                transaction.set_rollback(True)
        if not options['dry_run'] and removed:
            clear_page_cache()
        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}{len(pairs)} pairs listed: {found} between existing components, {missing} not on the site; '
            f'{removed} cross-reference rows removed ({removed // 2} links) across {touched.count()} components'))
