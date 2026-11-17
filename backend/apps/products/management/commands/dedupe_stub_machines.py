"""
Fold the stub machine products (import source norway-machine) that name one machine several ways into one page.

    manage.py dedupe_stub_machines [--dry-run] [--verbose]

For every stub, its name is cleaned (apps.products.stub_names: typo'd family words corrected to the brand's own
spelling, a repeated brand, junk words, screen sizes and trailing project codes dropped) and the site is searched
for the product the cleaned name denotes:
- a real (non-stub) product with the same brand and model key and compatible family words: the stub is merged
  into it ('Dell Inspirion 15-3567' into the site's 'Dell 15-3567');
- another stub whose family words contain this one's: merged into that stub ('Lenovo IdeaPad 5-14ARE05' into
  'Lenovo IdeaPad Flex 5-14ARE05'); among equals the shorter name survives;
- nothing: the stub stays, renamed to the cleaned form when that differs ('Flex 5-14ARE05. LC55-14A' -> 'Flex 5-14ARE05').
A stub whose cleaned name has no model left (its "model" was another maker's board code: 'HP Asus M2NC51-AR') is
deleted with its links. Merging moves the stub's links (a duplicate link is dropped, approval kept), photos,
documents and firmware to the survivor, drops the stub's review rows, and deletes the stub; a stub a moderator
had approved makes the survivor approved. Re-running changes nothing. Runs the same on dev and prod (no media).
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.merging import delete_product, merge_product
from apps.products.models import Product
from apps.products.stub_names import Resolver

STUB_PREFIX = 'norway-machine'


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = 'Merge stub machine products that name one machine several ways'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--verbose', action='store_true', help='print every merge, rename and deletion')

    def handle(self, *args, **opts):
        self.verbose = opts['verbose']
        self.n = Counter()
        self.lines = []
        try:
            with transaction.atomic():
                self.run()
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            pass
        for line in self.lines:
            self.stdout.write(line)
        self.stdout.write(', '.join(f'{k} {v}' for k, v in sorted(self.n.items())) + (' (dry run)' if opts['dry_run'] else ''))

    def say(self, kind, text):
        self.n[kind] += 1
        if self.verbose:
            self.lines.append(f'{kind}: {text}')

    def run(self):
        r = Resolver()
        stubs = list(Product.objects.filter(import_source__startswith=STUB_PREFIX).order_by('manufacturer', 'model_number'))
        self.n['stubs'] = len(stubs)
        # the widest names first, so a group's survivor is settled before its narrower spellings look for it
        cleaned = {s.pk: r.clean(s.manufacturer, s.model_number) for s in stubs}
        stubs.sort(key=lambda s: (-len(cleaned[s.pk].family) if cleaned[s.pk] else 0,
                                  0 if cleaned[s.pk] and cleaned[s.pk].name == s.model_number else 1, len(s.model_number)))
        gone = set()
        for s in stubs:
            if s.pk in gone:
                continue
            c = cleaned[s.pk]
            if c is None:
                self.say('deleted (no machine model)', f'{s.manufacturer} {s.model_number}')
                self.remove(s, r)
                gone.add(s.pk)
                continue
            target = r.find(s.manufacturer, c, exclude_pk=s.pk, category=s.category, stubs_only_if_wider=True,
                            self_name=s.model_number)
            if target is not None and target.pk not in gone:
                kind = 'merged into product' if not target.import_source.startswith(STUB_PREFIX) else 'merged into stub'
                self.say(kind, f'{s.manufacturer} {s.model_number} -> {target.manufacturer} {target.model_number}')
                self.merge(s, target, r)
                gone.add(s.pk)
            elif c.name.lower() != s.model_number.lower():        # a change of case alone is not worth a rename
                if Product.objects.filter(manufacturer=s.manufacturer, model_number=c.name).exclude(pk=s.pk).exists():
                    self.say('kept (cleaned name taken)', f'{s.manufacturer} {s.model_number} ~ {c.name}')
                    continue
                self.say('renamed', f'{s.manufacturer} {s.model_number} -> {c.name}')
                r.forget(s)
                s.model_number = c.name
                s.save(update_fields=['model_number'])
                r.remember(s)
            else:
                self.n['unchanged'] += 1

    def merge(self, stub, target, r):
        merge_product(stub, target, self.n)
        r.forget(stub)

    def remove(self, stub, r):
        delete_product(stub)
        r.forget(stub)
