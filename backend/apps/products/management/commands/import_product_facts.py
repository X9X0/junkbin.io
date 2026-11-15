"""
Apply facts found about existing products - which boards sit inside a machine, the maker's order
numbers for them - without re-running the lane that created the products.

    manage.py import_product_facts FACTS.json [--dry-run]

FACTS.json: [{"product_id": "<uuid>", "boards": [{"maker": "Lenovo", "code": "NM-A271", "n": 5}],
              "parts": ["Lenovo FRU 5B20G36639"], "used_in": ["HP Pavilion a1250n"],
              "evidence": "named with the Lenovo G50-70 in 12 parts listings"}]

For each product: one sentence 'Boards inside: ... (web search).' (a machine: the boards named for it,
its mainboard's order numbers) or 'Used in: ... (web search).' (a board: the machines named for it) is
written into, or replaced in, its description. Every board code that is a product on the site (any
revision) becomes a ProductLink part -> this host; every machine name that is exactly a product
becomes a ProductLink this part -> host. Links are unapproved and tagged norway-board-links:web:<product id>
so the norway-board-links review batch gates them; links under that tag the facts no longer name are
removed. Idempotent.
"""
import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.models import Product, ProductLink
from .import_board_bom import Command as Importer

SENTENCE = re.compile(r'\s*(?:Boards inside|Used in|Sold as|Also sold as|OEM board for|Also called|[A-Za-z]+ [A-Za-z0-9/+ ]+ chipset|[Ss]ocket )'
                      r'.*?\(web search\)\.', re.S)


def facts_sentence(boards, parts, used_in=(), aliases=(), notes=()):
    """notes: free sentences from spec pages ('OEM board for HP (HP name Leonite)', 'Intel 945P chipset, socket LGA 775,
    micro-ATX'); they come first so the sentence still starts with a known marker for SENTENCE to find again."""
    bits = [n[0].upper() + n[1:] for n in notes if n]
    if boards:
        bits.append('Boards inside: ' + ', '.join(f"{b['maker']} {b['code']}" for b in boards))
    if aliases:
        bits.append('Also sold as: ' + ', '.join(aliases[:4]))
    if used_in:
        bits.append('Used in: ' + ', '.join(used_in[:8]))
    if parts:
        bits.append(('Mainboard sold as ' if boards else 'Sold as ') + ', '.join(parts[:6]))
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
        boards, parts, used_in = f.get('boards', []), f.get('parts', []), f.get('used_in', [])
        new_desc = SENTENCE.sub('', product.description).rstrip() \
            + facts_sentence(boards, parts, used_in, f.get('aliases', []), f.get('notes', []))
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
        hosts = {}
        for name in used_in:
            found = Importer.host_products(name, exclude_tag_prefix=None)      # any product may be the machine
            for host in found:
                if host.pk != product.pk:
                    hosts[host.pk] = (host, f"{product.manufacturer} {product.model_number} is "
                                            f"{f.get('evidence', 'named for this machine')} ({name}).")
        ours = {(l.part_id, l.host_id): l for l in ProductLink.objects.filter(import_source=tag)}
        want_keys = {(pk, product.pk) for pk in wanted} | {(product.pk, pk) for pk in hosts}
        for key, l in ours.items():
            if key not in want_keys:
                totals['links_removed'] += 1
                if not dry_run:
                    l.delete()
        pairs = [(part, product, ev) for part, ev in wanted.values()] + [(product, host, ev) for host, ev in hosts.values()]
        for part, host, evidence in pairs:
            if (part.pk, host.pk) in ours or ProductLink.objects.filter(part=part, host=host, kind=ProductLink.Kind.FITTED_IN).exists():
                totals['links_kept'] += 1
                continue
            totals['links_added'] += 1
            if not dry_run:
                ProductLink.objects.create(part=part, host=host, kind=ProductLink.Kind.FITTED_IN,
                                           evidence=evidence[:1000], import_source=tag, is_approved=False)
