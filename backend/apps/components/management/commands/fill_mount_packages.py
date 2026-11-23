"""Parts with no package whose boards all say how they are mounted get the mounting-only label the board implies
(apps.components.mounting): 'SMD' for the chips on a factory-BOM mainboard, 'Axial' for the resistors and diodes
of an amplifier schematic. A part is labelled only when every one of its placements implies the same label; a
part shared with a board that says nothing (a service manual's parts list) or that disagrees is left alone.

    manage.py fill_mount_packages [--apply] [--type resistor]

Without --apply, reports the counts per type and label."""
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.components.models import Component, ProductComponent
from apps.components.mounting import mount_default


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--type', help='only this component type')

    def handle(self, *args, **opts):
        comps = Component.objects.filter(package_type='')
        if opts['type']:
            comps = comps.filter(component_type=opts['type'])
        sources = defaultdict(set)
        for cid, src in ProductComponent.objects.filter(component__in=comps).values_list('component_id', 'import_source'):
            sources[cid].add(src or '')
        n = Counter()
        planned = defaultdict(list)
        for c in comps.only('pk', 'component_type', 'specifications'):
            labels = {mount_default(src, c.component_type, c.specifications) for src in sources.get(c.pk, ())}
            if len(labels) != 1 or '' in labels:
                n['unplaced' if not labels else 'mixed or unknown'] += 1
                continue
            label = labels.pop()
            planned[label].append(c.pk)
            n[f'{c.component_type} -> {label}'] += 1
        if opts['apply']:
            with transaction.atomic():
                for label, pks in planned.items():
                    Component.objects.filter(pk__in=pks).update(package_type=label)
        prefix = '' if opts['apply'] else 'DRY RUN - '
        self.stdout.write(prefix + ', '.join(f'{k} {v}' for k, v in sorted(n.items())))
