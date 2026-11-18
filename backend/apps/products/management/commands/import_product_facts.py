"""
Apply facts found about existing products - which boards sit inside a machine, the maker's order
numbers for them - without re-running the lane that created the products.

    manage.py import_product_facts FACTS.json [MORE.json ...] [--dry-run]

Give every facts file of a run together: entries for one product and source are merged across files (a desktop board
that is also in the devices file), so none of them overwrites another's sentence or links.

FACTS.json: [{"product_id": "<uuid>", "product": {"manufacturer": "Lenovo", "model_number": "G50-70", "revision": ""},
              "boards": [{"maker": "Lenovo", "code": "NM-A271", "n": 5}],
              "parts": ["Lenovo FRU 5B20G36639"], "used_in": ["HP Pavilion a1250n"],
              "evidence": "named with the Lenovo G50-70 in 12 parts listings"}]

"product" is the fallback key: when no product has that id here (the lane that made it has not been
published yet, or re-created it with a new id), every product with that manufacturer, model number and
revision takes the facts instead.

For each product: one sentence 'Boards inside: ... (web search).' (a machine: the boards named for it,
its mainboard's order numbers) or 'Used in: ... (web search).' (a board: the machines named for it) is
written into, or replaced in, its description. Every board code that is a product on the site (any
revision) becomes a ProductLink part -> this host; every machine name that is exactly a product
becomes a ProductLink this part -> host. Links are unapproved and tagged norway-board-links:web:<product id>
so the norway-board-links review batch gates them; links under that tag the facts no longer name are
removed. Idempotent.

Stubs (2026-11-15): a board code with no board product becomes one (unapproved, tag
norway-board-stub:<Maker>_<code>, batch norway-board-stub) when two or more listings name it for the
machine, or a BIOS dump label does; a machine name with no product becomes a stub machine (batch
norway-machine) under import_board_bom's rules when the board's listings number two or more. A stub
board is removed as soon as a schematic lane brings the real board.
"""
import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.models import Product, ProductLink
from .import_board_bom import Command as Importer

SOURCES = ('web search', 'firmware label', 'service manual')
MARKERS = r'(?:Boards inside|Used in|Sold as|Also sold as|Mainboard sold as|OEM board for|Also called|[A-Za-z]+ [A-Za-z0-9/+ ]+ chipset|[Ss]ocket )'


def sentence_patterns(source):
    """The facts sentence an earlier run of this source wrote: from a known first word to '(source).', and, for a
    sentence starting with none of those words ('ATX (web search).', a bare form factor), one without periods or
    parentheses inside, so it cannot reach into the product's own text."""
    src = re.escape(source)
    any_end = r'\((?:' + '|'.join(map(re.escape, SOURCES)) + r')\)\.'
    # from a marker to this source's end, never running over another sentence's end on the way
    return (re.compile(r'\s*' + MARKERS + r'(?:(?!' + any_end + r').)*?\(' + src + r'\)\.', re.S),
            re.compile(r'\s*[^.()]*\(' + src + r'\)\.'))
BOARD_STUB_TAG = 'norway-board-stub'
MAKERS = {'Compal', 'Quanta', 'Lenovo', 'Wistron', 'Inventec', 'Samsung', 'Apple', 'Foxconn', 'Pegatron'}


def merged_entries(facts):
    """One entry per product: a file naming a product twice (a board under two schematic revisions) would otherwise
    have the second entry remove the first one's links on every run."""
    out, by_key = [], {}
    for f in facts:
        key = (f['product_id'], f.get('source', 'web search'))
        if key not in by_key:
            by_key[key] = dict(f)
            out.append(by_key[key])
            continue
        m = by_key[key]
        for field in ('boards', 'parts', 'used_in', 'aliases', 'notes'):
            seen = {json.dumps(x, sort_keys=True) for x in m.get(field, [])}
            m[field] = list(m.get(field, [])) + [x for x in f.get(field, []) if json.dumps(x, sort_keys=True) not in seen]
        if not m.get('product') and f.get('product'):
            m['product'] = f['product']
    return out


def strip_facts(description, source):
    """The description without any facts sentence an earlier run of this source wrote (however many copies: a run
    before 2026-11-18 could add a bare note like 'ATX (web search).' again each time). Other sources' sentences stay."""
    marked, bare = sentence_patterns(source)
    text = description
    while True:
        cleaned = bare.sub('', marked.sub('', text))
        if cleaned == text:
            return text.rstrip()
        text = cleaned


def with_facts(description, source, sentence, notes=()):
    """The description with this source's facts sentence in the place its earlier one had (so a machine known from a
    firmware label and from web search keeps both sentences in a stable order), or appended when there was none.
    Note sentences a run before 2026-11-18 left in front of the marked sentence ('Micro-ATX. Micro-ATX. Used in: ...')
    are removed."""
    marked, bare = sentence_patterns(source)
    m = marked.search(description) or bare.search(description)
    if not m:
        return strip_facts(description, source) + sentence
    head, tail = description[:m.start()].rstrip(), strip_facts(description[m.end():], source)
    orphans = tuple(n[0].upper() + n[1:] + '.' for n in notes if n)
    while orphans and head.endswith(orphans):
        head = head[:head.rfind(' ')].rstrip() if ' ' in head else ''
    return (head + sentence + (' ' + tail.lstrip() if tail else '')).rstrip()


def facts_sentence(boards, parts, used_in=(), aliases=(), notes=(), source='web search'):
    """notes: free sentences from spec pages ('OEM board for HP (HP name Leonite)', 'Intel 945P chipset, socket LGA 775,
    micro-ATX'); they come last, so the group starts with a known marker whenever it has one (a notes-only group
    starts with the note, which sentence_patterns' bare form or the chipset/OEM markers find again)."""
    bits = []
    if boards:
        bits.append('Boards inside: ' + ', '.join(f"{b['maker']} {b['code']}" for b in boards))
    if aliases:
        bits.append('Also sold as: ' + ', '.join(aliases[:4]))
    if used_in:
        bits.append('Used in: ' + ', '.join(used_in[:8]))
    if parts:
        bits.append(('Mainboard sold as ' if boards else 'Sold as ') + ', '.join(parts[:6]))
    bits += [n[0].upper() + n[1:] for n in notes if n]
    return (' ' + '. '.join(bits) + f' ({source}).') if bits else ''


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('facts', nargs='+')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        Importer._resolver = None                        # a fresh view of the site's names for this run
        facts = []
        for path in opts['facts']:
            with open(path, encoding='utf-8') as fh:
                facts += json.load(fh)
        facts = merged_entries(facts)
        totals = {'products': 0, 'by_name': 0, 'missing': 0, 'descriptions_changed': 0, 'links_added': 0, 'links_kept': 0,
                  'links_removed': 0, 'codes_without_product': 0, 'board_stubs_created': 0, 'board_stubs_retired': 0,
                  'machines_created': 0}
        with transaction.atomic():
            for f in facts:
                products = list(Product.objects.filter(pk=f['product_id']))
                if not products and f.get('product'):
                    k = f['product']
                    products = list(Product.objects.filter(manufacturer__iexact=k['manufacturer'], model_number__iexact=k['model_number'],
                                                           revision=k.get('revision', '')))
                    totals['by_name'] += bool(products)
                if not products:
                    totals['missing'] += 1
                    continue
                for product in products:
                    totals['products'] += 1
                    self.apply(product, f, opts['dry_run'], totals)
            if opts['dry_run']:
                transaction.set_rollback(True)
        self.stdout.write(('DRY RUN (rolled back) - ' if opts['dry_run'] else '')
                          + ', '.join(f'{k.replace("_", " ")} {v}' for k, v in totals.items()))

    @staticmethod
    def board_stub_allowed(b, source):
        """Two or more listings, or a BIOS label, and a maker the lanes know."""
        return b.get('maker') in MAKERS and (source != 'web search' or b.get('n', 0) >= 2)

    @staticmethod
    def board_stub(machine, b, source, f, dry_run, totals):
        """A board product for a code no schematic lane has brought yet, so the machine links to it and other
        machines naming the same code meet there. Tagged norway-board-stub:<Maker>_<code>; the facts of the next
        machine naming the code find it by model number."""
        totals['board_stubs_created'] += 1
        if dry_run:
            return None
        maker, code = b['maker'], b['code']
        how = (f"the BIOS dump label of the {machine.manufacturer} {machine.model_number}" if source == 'firmware label'
               else f"{b.get('n', 0)} parts listings found by web search, which name it for the {machine.manufacturer} {machine.model_number}")
        words = 'notebook mainboard' if machine.category == 'laptop' else 'mainboard'
        extra = (f" Wistron files the board by its PCB number {code}; listings add the revision after a dash." if maker == 'Wistron' else '')
        return Product.objects.create(
            manufacturer=maker, model_number=code, category=machine.category if machine.category in ('laptop', 'desktop', 'tablet', 'phone') else 'laptop',
            subcategory='Mainboard',
            description=f"{maker} {code} {words}, known from {how}.{extra} No schematic in the collection yet.",
            import_source=f'{BOARD_STUB_TAG}:{maker}_{code}', is_approved=False)

    @staticmethod
    def apply(product, f, dry_run, totals):
        boards, parts, used_in = f.get('boards', []), f.get('parts', []), f.get('used_in', [])
        source = f.get('source', 'web search')
        if source not in SOURCES:
            raise CommandError(f'unknown facts source {source!r}')
        new_desc = with_facts(product.description, source,
                              facts_sentence(boards, parts, used_in, f.get('aliases', []), f.get('notes', []), source),
                              f.get('notes', []))
        if new_desc != product.description:
            totals['descriptions_changed'] += 1
            if not dry_run:
                product.description = new_desc
                product.save(update_fields=['description'])
        tag = f"norway-board-links:{'web' if source == 'web search' else source.split()[0]}:{product.pk}"
        wanted = {}
        for b in boards:
            found = list(Product.objects.filter(model_number__iexact=b['code'], import_source__startswith='norway-board'))
            real = [p for p in found if not p.import_source.startswith(f'{BOARD_STUB_TAG}:')]
            if real and len(real) < len(found):             # a schematic lane brought the board: the stub goes
                for stub in found:
                    if stub not in real:
                        totals['board_stubs_retired'] += 1
                        if not dry_run:
                            stub.delete()
                found = real
            allowed = not found and Command.board_stub_allowed(b, source)
            if allowed:
                stub = Command.board_stub(product, b, source, f, dry_run, totals)
                found = [stub] if stub else []
            if not found and not (dry_run and allowed):
                totals['codes_without_product'] += 1
            for part in found:
                if part.pk != product.pk:
                    wanted[part.pk] = (part, f"{part.manufacturer} {part.model_number} is {f.get('evidence', 'named with this machine')}.")
        hosts = {}
        listings = re.search(r'in (\d+) parts listings', f.get('evidence', ''))
        strong = source != 'web search' or (listings and int(listings.group(1)) >= 2)
        for name in used_in:
            found = Importer.host_products(name, exclude_tag_prefix=None)      # any product may be the machine
            if not found and strong:
                stub = Importer.make_stub(
                    name, product.category if product.category in ('desktop', 'laptop') else 'laptop',
                    tag=f'{Importer.STUB_TAG}:facts:{product.pk}',
                    describe=lambda brand, model: (
                        f"{brand} {model}: known from parts listings found by web search that name it for the "
                        f"{product.manufacturer} {product.model_number} mainboard. It uses that board. No manual, firmware or photos yet."),
                    user=None, dry_run=dry_run, result=totals)
                found = [stub] if stub else []
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
