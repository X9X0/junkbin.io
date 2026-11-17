"""
Correct typo'd family words in imported machine names ('Lenovo ThinaPad E540' -> 'Lenovo ThinkPad E540').

    manage.py fix_family_typos [--dry-run] [--verbose]

Looks at imported products in a machine category (desktop, laptop, tablet, phone) whose import source is not a
stub machine (those are dedupe_stub_machines' job) and that have a model token (a word with a digit). The words in
front of the model token are each corrected only to a spelling the brand's own products already use
(apps.products.stub_names.Resolver.fix_word: a near miss of a word two or more of the brand's products carry,
never a known family word, never a case-only change, never a word that merely contains or is contained in the
other: 'Duo-Medalist' is not 'Medalist'). A looser miss ('Protage' for 'Portege') is accepted only against a word
the brand uses on ten or more products, starting with the same letter. A leading word that repeats the brand or
is its letters rearranged ('Levono ThinkPad SL410') is dropped. Everything from the model token on is kept as
written; the description's leading mention of the old name follows the rename. Slugs are kept, so URLs keep working.

When the corrected name is already a page: a stub machine holding it is folded into the corrected product
(the stub is the machine lane's copy of the same machine), and a real product holding it absorbs the typo'd one
(links, photos, documents, firmware and approval move; see apps.products.merging). Re-running changes nothing.
Runs the same on dev and prod.
"""
import difflib
import re
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.merging import merge_product
from apps.products.models import Product
from apps.products.stub_names import KNOWN_FAMILIES, MACHINE_CATEGORIES, Resolver

STUB_PREFIX = 'norway-machine'
COMMON = 10                                      # products a family word must be on before a looser miss of it counts


def counts(resolver, brand):
    """{family word: number of the brand's non-stub products that carry it}, cached on the resolver."""
    cache = resolver.__dict__.setdefault('_counts', {})
    b = brand.lower()
    if b not in cache:
        c = Counter()
        for model in Product.objects.filter(manufacturer__iexact=brand).exclude(
                import_source__startswith=STUB_PREFIX).values_list('model_number', flat=True):
            for w in model.split():
                if re.search(r'\d', w):
                    break
                c[w.strip('.,;:()[]').lower()] += 1
        cache[b] = c
    return cache[b]


def fix_word(resolver, brand, word):
    """The brand's spelling of a family word (see Resolver.fix_word), with the looser second chance; '' drops it."""
    w = word.lower()
    b = brand.lower()
    vocab = resolver.vocab(brand)
    if w == b or (w not in vocab and w not in KNOWN_FAMILIES and len(w) == len(b) and sorted(w) == sorted(b)):
        return ''                                                     # 'Dell Dell ...', 'Levono ThinkPad': the brand again
    fixed = resolver.fix_word(brand, word)
    if fixed.lower() != w or w in vocab or w in KNOWN_FAMILIES or len(w) < 5:
        return fixed
    common = [v for v, k in counts(resolver, brand).items() if k >= COMMON and v in vocab and v[0] == w[0] and len(v) >= 5]
    close = difflib.get_close_matches(w, common, n=1, cutoff=0.7)
    return vocab[close[0]] if close else word


class DryRun(Exception):
    pass


def corrected(resolver, brand, model):
    """The name with its family words corrected, or None when nothing changes or no model token follows them."""
    words = model.split()
    out, changed = [], False
    for i, w in enumerate(words):
        if re.search(r'\d', w):
            if not changed:
                return None
            out.extend(words[i:])
            return ' '.join(out)
        bare = w.strip('.,;:()[]')
        fixed = fix_word(resolver, brand, bare)
        if not fixed:
            changed = True                                            # the brand repeated: dropped
        elif fixed.lower() != bare.lower() and bare.lower() not in fixed.lower() and fixed.lower() not in bare.lower():
            out.append(w.replace(bare, fixed))
            changed = True
        else:
            out.append(w)
    return None                                                       # no model token: not a machine name


class Command(BaseCommand):
    help = "Correct typo'd family words in imported machine names"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--verbose', action='store_true', help='print every rename and merge')

    def handle(self, *args, **opts):
        n = Counter()
        lines = []
        r = Resolver()
        try:
            with transaction.atomic():
                qs = (Product.objects.exclude(import_source='').exclude(import_source__startswith=STUB_PREFIX)
                      .filter(category__in=MACHINE_CATEGORIES).order_by('manufacturer', 'model_number'))
                for p in qs:
                    new = corrected(r, p.manufacturer, p.model_number)
                    if not new:
                        continue
                    holder = Product.objects.filter(manufacturer=p.manufacturer, model_number=new, revision=p.revision,
                                                    region=p.region).exclude(pk=p.pk).first()
                    if holder is not None and not holder.import_source.startswith(STUB_PREFIX):
                        n['merged into the corrected page'] += 1
                        lines.append(f'merged: {p.manufacturer} {p.model_number!r} -> {new!r} [{holder.import_source}]')
                        merge_product(p, holder, n)
                        continue
                    if holder is not None:
                        n['stubs folded in'] += 1
                        lines.append(f'stub folded in: {p.manufacturer} {new!r} [{holder.import_source}] -> {p.model_number!r}')
                        merge_product(holder, p, n)
                        p.refresh_from_db()
                    n['renamed'] += 1
                    lines.append(f'renamed: {p.manufacturer} {p.model_number!r} -> {new!r}  [{p.import_source}]')
                    old = f'{p.manufacturer} {p.model_number}'
                    fields = ['model_number']
                    if p.description and p.description.startswith(old):
                        p.description = f'{p.manufacturer} {new}' + p.description[len(old):]
                        fields.append('description')
                    p.model_number = new
                    p.save(update_fields=fields)
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            pass
        if opts['verbose']:
            for line in lines:
                self.stdout.write(line)
        self.stdout.write((', '.join(f'{k} {v}' for k, v in sorted(n.items())) or 'nothing to change')
                          + (' (dry run)' if opts['dry_run'] else ''))
