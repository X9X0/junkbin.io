"""
One machine under two spellings, one of them carrying the screen size the maker prints in its marketing name
('Dell Inspiron 3542' and 'Dell Inspiron 15 3542'; 'Apple MacBook Pro A1398' and 'Apple MacBook Pro 15 A1398'):
the pages are merged into the sized name (user's choice, 2026-11-20).

    manage.py merge_sized_twins [--dry-run] [--verbose]

A group is every imported, non-stub machine of one brand whose names clean to the same family words and model key
(apps.products.stub_names) where at least one name carries a size and one does not. The survivor is the sized
spelling, a space between size and model preferred over a dash ('Inspiron 15 3542' over 'Inspiron 15-3542'); the
others fold into it with apps.products.merging (links, firmware, photos, documents, placements, approval). Stub
machines are left to dedupe_stub_machines. Re-running changes nothing. Runs the same on dev and prod.
"""
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.merging import merge_product
from apps.products.models import Product
from apps.products.stub_names import MACHINE_CATEGORIES, Resolver


class DryRun(Exception):
    pass


def groups():
    """{(brand, key, family): [(product, cleaned)]} for the twin groups."""
    r = Resolver()
    by_key = defaultdict(list)
    qs = (Product.objects.exclude(import_source='').exclude(import_source__startswith='norway-machine')
          .filter(category__in=MACHINE_CATEGORIES).order_by('manufacturer', 'model_number'))
    for p in qs:
        c = r.clean(p.manufacturer, p.model_number)
        if c and c.key:
            by_key[(p.manufacturer.lower(), c.key, tuple(sorted(c.family_set)))].append((p, c))
    return {k: v for k, v in by_key.items()
            if len(v) > 1 and any(c.size for _, c in v) and any(not c.size for _, c in v)
            and len({c.size for _, c in v if c.size}) == 1}


def survivor(members):
    sized = [(p, c) for p, c in members if c.size]
    sized.sort(key=lambda pc: (0 if f' {pc[1].size} ' in f' {pc[0].model_number} ' else 1, len(pc[0].model_number), str(pc[0].pk)))
    return sized[0][0]


class Command(BaseCommand):
    help = 'Merge a machine named with and without its screen size into the sized name'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **opts):
        n = Counter()
        lines = []
        try:
            with transaction.atomic():
                for key, members in groups().items():
                    keep = survivor(members)
                    for p, c in members:
                        if p.pk == keep.pk:
                            continue
                        n['merged'] += 1
                        lines.append(f'{p.manufacturer} {p.model_number!r} -> {keep.model_number!r}')
                        merge_product(p, keep, n)
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            pass
        if opts['verbose']:
            for line in lines:
                self.stdout.write(line)
        self.stdout.write((', '.join(f'{k} {v}' for k, v in sorted(n.items())) or 'nothing to merge')
                          + (' (dry run)' if opts['dry_run'] else ''))
