"""
Apply facts found about existing products - which boards sit inside a machine, the maker's order
numbers for them - without re-running the lane that created the products.

    manage.py import_product_facts FACTS.json [--dry-run]

FACTS.json: [{"product_id": "<uuid>", "boards": [{"maker": "Lenovo", "code": "NM-A271", "n": 5}],
              "parts": ["Lenovo FRU 5B20G36639"], "evidence": "named with the Lenovo G50-70 in 12 parts listings"}]

For each product: one sentence 'Boards inside: ... (web search).' is written into (or replaced in)
its description; every board code that is a product on the site (any revision) becomes a ProductLink
part -> this host, unapproved, tagged norway-board-links:web:<product id> so the norway-board-links
review batch gates it; links under that tag the facts no longer name are removed. Idempotent.
"""
import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.models import Product, ProductLink

SENTENCE = re.compile(r'\s*Boards inside: .*?\(web search\)\.', re.S)


def facts_sentence(boards, parts):
    bits = []
    if boards:
        bits.append('Boards inside: ' + ', '.join(f"{b['maker']} {b['code']}" for b in boards))
    if parts:
        bits.append(('Mainboard sold as ' if boards else 'Boards inside: mainboard sold as ') + ', '.join(parts[:6]))
    return (' ' + '. '.join(bits) + ' (web search).') if bits else ''


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('facts')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        with open(opts['facts'], encoding='utf-8') as fh:
            facts = json.load(fh)
        totals = {'products': 0, 'missing': 0, 'descriptions_changed': 0, 'links_added': 0, 'links_kept': 0,
                  'links_removed': 0, 'codes_without_product': 0}
        with transaction.atomic():
            for f in facts:
                product = Product.objects.filter(pk=f['product_id']).first()
                if not product:
                    totals['missing'] += 1
                    continue
                totals['products'] += 1
                self.apply(product, f, opts['dry_run'], totals)
            if opts['dry_run']:
                transaction.set_rollback(True)
        self.stdout.write(('DRY RUN (rolled back) - ' if opts['dry_run'] else '')
                          + ', '.join(f'{k.replace("_", " ")} {v}' for k, v in totals.items()))

    @staticmethod
    def apply(product, f, dry_run, totals):
        boards, parts = f.get('boards', []), f.get('parts', [])
        new_desc = SENTENCE.sub('', product.description).rstrip() + facts_sentence(boards, parts)
        if new_desc != product.description:
            totals['descriptions_changed'] += 1
            if not dry_run:
                product.description = new_desc
                product.save(update_fields=['description'])
        tag = f'norway-board-links:web:{product.pk}'
        wanted = {}
        for b in boards:
            found = list(Product.objects.filter(model_number__iexact=b['code'], import_source__startswith='norway-board:'))
            if not found:
                totals['codes_without_product'] += 1
            for part in found:
                if part.pk != product.pk:
                    wanted[part.pk] = (part, f"{part.manufacturer} {part.model_number} is {f.get('evidence', 'named with this machine')}.")
        ours = {l.part_id: l for l in ProductLink.objects.filter(host=product, import_source=tag)}
        for pk, l in ours.items():
            if pk not in wanted:
                totals['links_removed'] += 1
                if not dry_run:
                    l.delete()
        for pk, (part, evidence) in wanted.items():
            if pk in ours or ProductLink.objects.filter(part=part, host=product, kind=ProductLink.Kind.FITTED_IN).exists():
                totals['links_kept'] += 1
                continue
            totals['links_added'] += 1
            if not dry_run:
                ProductLink.objects.create(part=part, host=product, kind=ProductLink.Kind.FITTED_IN,
                                           evidence=evidence[:1000], import_source=tag, is_approved=False)
