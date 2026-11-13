"""
Confirm the Generic chips whose names are a label or a BOM line, not a part number.

    python manage.py confirm_schematic_chips report
    python manage.py confirm_schematic_chips verify [--budget 400] [--reserve 150] [--mouser-budget 400]
    python manage.py confirm_schematic_chips apply [--dry-run]

Two populations, one pipeline:

  labels   rows the schematic extractor marked for review: the chip's label is its part
           number (1N4148S, NPN-3904LT1-S-SOT23, LT1087S). See chip_labels.
  lines    Generic non-passive parts named by a whole factory-BOM line ('ADI AD1981B(R0.2)
           TQFP48 AC97 SOUNDMAX CODEC'), left that way because nothing confirmed the part
           number in the line. The part-shaped words in the line are the candidates.

Three kinds of answer, written to the component the rows point at:

  standard   the label names an industry-standard number (1N4148S -> 1N4148, NPN-3904LT1
             -> MMBT3904LT1, BAT54A-S-SOT23 -> BAT54A): any maker's part fits, so the row is
             confirmed as a Generic part of the standard number. No distributor call.
  confirmed  DigiKey (or, when it has nothing, Mouser) lists exactly a candidate number: the
             part takes that maker and number (NDS351AN-S-SOT23 -> onsemi NDS351AN). When no
             distributor has the bare number but DigiKey lists it with a short ordering suffix
             (LT1087 -> LT1087CT#PBF, LT1087IT#PBF) the family is confirmed: the part takes the
             maker when all such listings share one, else stays Generic (LM358: TI, onsemi,
             ST all make it), and keeps the bare number. `verify`
             asks, within the daily budget, and records every answer in VERDICTS
             (backend/.import_tmp/chip_verify/verdicts.json) so `apply` on prod needs no
             calls - push that file along with the code.
  junk       (labels only) no distributor knows it and it is a net name or a bare package
             (DMICLK100P, VCC33USB4, SOT-223): the rows are removed and the part deleted.

Everything else stays as it is; the labels stay marked for review and the moderation queue
lists them (import_review). `apply` moves rows onto an existing component of the same maker
and number when there is one, keeps the old name in alternative_part_numbers, sets the
package the label named, and replaces the review note. Safe to re-run; --dry-run reports
and rolls back.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.components.distributors import DistributorError, get_digikey, get_mouser, same_mpn
from apps.components.external_search import DIGIKEY_RESERVE, digikey_keyword, normalise
from apps.components.makers import canonical_maker
from apps.components.models import Component, ProductComponent
from apps.products import chip_labels
from apps.products.import_review import UNCONFIRMED as UNCONFIRMED_LINE
from apps.products.management.commands.extract_schematic_boms import UNCONFIRMED
from apps.products.management.commands.import_board_bom import refresh_usage_counts
from apps.products.models import Product

VERDICTS = Path('/app/.import_tmp/chip_verify/verdicts.json')
TAG = 'schematic-bom:'
PASSIVE = ('resistor', 'capacitor', 'inductor', 'ferrite', 'fuse', 'crystal', 'vacuum_tube', 'potentiometer', 'thermistor',
           'transformer', 'speaker', 'connector', 'switch', 'relay', 'battery', 'display')
STANDARD_NOTE = 'industry-standard type number read from the schematic label; any maker\'s part of this number fits'
CONFIRMED_NOTE = 'part number read from the schematic label, confirmed at {source}'
CONFIRMED_LINE_NOTE = 'part number read from the factory BOM line, confirmed at {source}'
PREFIX_SUFFIX_MAX = 6                 # 'LT1087' -> 'LT1087CT#PBF': an ordering suffix, not another part
# one company under its old and new names: listings under both are one maker, named by the first
FAMILIES = [
    ('Nexperia', 'NXP', 'Philips', 'NXP Semiconductors'),
    ('onsemi', 'Fairchild (onsemi)', 'Fairchild Semiconductor', 'Fairchild', 'Motorola', 'ON Semiconductor'),
    ('Renesas', 'Intersil', 'Harris Corporation', 'Harris (Intersil)', 'Renesas (Intersil)', 'IDT (Renesas)', 'ICS (Renesas)',
     'Hitachi/Renesas', 'Renesas Electronics Corporation'),
    ('Texas Instruments', 'National Semiconductor (TI)', 'National Semiconductor', 'Burr-Brown', 'Texas Instruments (Chipcon)'),
    ('Analog Devices', 'Linear Technology', 'Maxim Integrated', 'Analog Devices (Linear Technology)'),
    ('Vishay', 'Vishay Siliconix', 'Siliconix', 'General Semiconductor', 'Vishay General Semiconductor'),
    ('Infineon', 'International Rectifier', 'Siemens (Infineon)', 'Infineon (Cypress)', 'Cypress'),
    ('Microchip Technology', 'Atmel (Microchip Technology)', 'SST (Microchip Technology)', 'Micrel (Microchip Technology)', 'Atmel', 'Micrel'),
    ('Diodes Incorporated', 'Zetex (Diodes Inc.)', 'Pericom (Diodes Inc.)', 'Zetex', 'Pericom'),
    ('Nuvoton', 'Winbond'),
]


def one_maker(makers):
    """The one maker a list of listing makers amounts to (its current name), or None when
    they are really different companies."""
    makers = [canonical_maker(m) or m for m in makers if m]
    if len(set(makers)) == 1:
        return makers[0]
    for family in FAMILIES:
        if all(m in family for m in makers):
            return family[0]
    return None


def review_rows():
    return ProductComponent.objects.filter(needs_review=True, import_source__startswith=TAG)


def work():
    """[(name, component_id, population, rows)] most-used first: the Generic parts the
    review rows point at ('labels'), then Generic non-passives named by a whole line ('lines')."""
    out = []
    q = (review_rows().values('component_id', 'component__part_number', 'component__manufacturer')
         .annotate(n=Count('id')).order_by('-n'))
    seen = set()
    for r in q:
        if r['component__manufacturer'] == 'Generic':
            out.append((r['component__part_number'], r['component_id'], 'labels', r['n']))
            seen.add(r['component_id'])
    lines = (Component.objects.filter(manufacturer='Generic').exclude(component_type__in=PASSIVE).exclude(pk__in=seen)
             .filter(part_number__regex=r'^\S+\s+\S+\s+\S+').order_by('-usage_count').values_list('part_number', 'pk', 'usage_count'))
    out += [(name, pk, 'lines', n) for name, pk, n in lines]
    return out


def candidates(name, population):
    return chip_labels.candidates(name) if population == 'labels' else chip_labels.line_candidates(name)


def load_verdicts():
    if VERDICTS.exists():
        return json.loads(VERDICTS.read_text())
    return {}


def save_verdicts(verdicts):
    VERDICTS.parent.mkdir(parents=True, exist_ok=True)
    VERDICTS.write_text(json.dumps(verdicts, indent=0, sort_keys=True))


def compact(hit, source):
    """The part of a distributor answer worth keeping. Its 'status' (Active, Obsolete) is
    stored as 'lifecycle' so it cannot overwrite the verdict's own status."""
    return {**{k: hit.get(k) for k in ('mpn', 'manufacturer', 'description', 'datasheet_url', 'category')},
            'lifecycle': hit.get('status'), 'sources': [source]}


def classify(name, population, verdicts):
    if population == 'labels' and chip_labels.standard_from_label(name):
        return 'standard'
    v = verdicts.get(name)
    if v and v.get('status') in ('confirmed', 'prefix'):
        return 'confirmed'
    if population == 'lines':
        return 'notfound' if v else ('unchecked' if candidates(name, population) else 'notfound')
    asked = bool(v) or not candidates(name, population)
    if asked and chip_labels.junk(name):
        return 'junk'                         # a net name no distributor knew, or a bare package
    return 'notfound' if asked else 'unchecked'


class Command(BaseCommand):
    help = 'Confirm, by rule or at a distributor, the Generic chips named by a schematic label or a BOM line'

    def add_arguments(self, parser):
        parser.add_argument('stage', choices=['report', 'verify', 'apply'])
        parser.add_argument('--budget', type=int, default=400, help='verify: DigiKey calls this run may spend')
        parser.add_argument('--reserve', type=int, default=DIGIKEY_RESERVE, help='verify: DigiKey calls to leave for the site')
        parser.add_argument('--mouser-budget', type=int, default=400, help='verify: Mouser calls this run may spend')
        parser.add_argument('--dry-run', action='store_true', help='apply: report and roll back')

    def handle(self, *args, **options):
        getattr(self, options['stage'])(options)

    # ---- report -------------------------------------------------------------------------
    def report(self, options):
        verdicts = load_verdicts()
        table = {}
        for name, _, population, n in work():
            cell = table.setdefault((population, classify(name, population, verdicts)), [0, 0])
            cell[0] += 1
            cell[1] += n
        for population in ('labels', 'lines'):
            for kind in ('standard', 'confirmed', 'junk', 'notfound', 'unchecked'):
                parts, rows = table.get((population, kind), (0, 0))
                if parts:
                    self.stdout.write(f'{population:7} {kind:10} parts {parts:5}  rows {rows:6}')
        self.stdout.write(f'verdicts on file: {len(verdicts)}; DigiKey calls left today: {cache.get("digikey_remaining")}')

    # ---- verify -------------------------------------------------------------------------
    def verify(self, options):
        import fcntl
        VERDICTS.parent.mkdir(parents=True, exist_ok=True)
        lock = open(VERDICTS.parent / 'verify.lock', 'w')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stdout.write('verify: another verify run holds the lock; nothing done')
            return
        verdicts = load_verdicts()
        digikey, mouser = get_digikey(), get_mouser()
        spent = {'digikey': 0, 'mouser': 0}
        checked = confirmed = 0
        stop = None
        for name, _, population, n in work():
            kind = classify(name, population, verdicts)
            earlier = verdicts.get(name) or {}
            if kind == 'notfound' and earlier and not earlier.get('prefix_checked'):
                exact_needed = False          # asked before the family search existed: ask for the family only
            elif kind != 'unchecked':
                continue
            else:
                exact_needed = True
            cands = candidates(name, population)
            if spent['digikey'] + len(cands) * (2 if exact_needed else 1) > options['budget']:
                stop = 'DigiKey budget for this run spent'
                break
            if digikey.remaining is not None and digikey.remaining <= options['reserve']:
                stop = f'DigiKey reserve reached ({digikey.remaining} left)'
                break
            verdict = {'status': 'notfound', 'tried': cands, 'population': population, 'prefix_checked': True,
                       'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
            try:
                for cand in cands:
                    hit, source = self.ask(cand, digikey, mouser, spent, options['mouser_budget']) if exact_needed else (None, None)
                    if hit:
                        verdict.update({'status': 'confirmed', 'candidate': cand, **compact(hit, source)})
                        confirmed += 1
                        break
                    family = self.family(cand, digikey, spent)
                    if family:
                        verdict.update({'status': 'prefix', 'candidate': cand, **family})
                        confirmed += 1
                        break
            except DistributorError as exc:
                stop = f'a distributor refused ({str(exc)[:120]})'
                break
            verdicts[name] = verdict
            checked += 1
            if checked % 25 == 0:
                save_verdicts(verdicts)
                self.stdout.write(f'  {checked} names checked, {confirmed} confirmed, DigiKey left {digikey.remaining}')
        save_verdicts(verdicts)
        if digikey.remaining is not None:
            cache.set('digikey_remaining', digikey.remaining, 6 * 3600)
        self.stdout.write(f'verify: {checked} names checked, {confirmed} confirmed; DigiKey calls {spent["digikey"]}, '
                          f'Mouser {spent["mouser"]}; verdicts on file {len(verdicts)}'
                          + (f'; stopped: {stop}' if stop else ''))

    @staticmethod
    def ask(cand, digikey, mouser, spent, mouser_budget):
        """(hit, source) for an exact match of cand: DigiKey first, Mouser only when DigiKey
        has nothing and the Mouser budget allows. Raises DistributorError when refused."""
        if digikey.is_configured:
            spent['digikey'] += 1
            hit = digikey.search_mpn(cand, None)
            time.sleep(0.4)
            if hit and same_mpn(hit.get('mpn'), cand):
                return hit, 'digikey'
        if mouser.is_configured and spent['mouser'] < mouser_budget:
            spent['mouser'] += 1
            hit = mouser.search_mpn(cand, None)
            time.sleep(2.1)                   # Mouser's per-minute limit (seen at 1 s spacing: 403 TooManyRequests)
            if hit and same_mpn(hit.get('mpn'), cand):
                return hit, 'mouser'
        return None, None

    @staticmethod
    def family(cand, digikey, spent):
        """DigiKey listings of cand plus a short ordering suffix (LT1087 -> LT1087CT#PBF): the
        family is real. {'manufacturer', 'makers', 'listed', 'description', 'datasheet_url',
        'sources'} with manufacturer None when several makers list it (a multi-sourced part),
        or None when nothing of the kind is listed."""
        base = normalise(cand)
        if not digikey.is_configured or len(base) < 5:
            return None
        spent['digikey'] += 1
        hits = digikey_keyword(digikey, cand, limit=10)
        time.sleep(0.4)
        hits = [h for h in hits if normalise(h.get('mpn')).startswith(base)
                and 0 < len(normalise(h.get('mpn'))) - len(base) <= PREFIX_SUFFIX_MAX]
        if not hits:
            return None
        makers = sorted({canonical_maker(h.get('manufacturer') or '') or h.get('manufacturer') for h in hits})
        best = max(hits, key=lambda h: h.get('stock') or 0)
        return {'manufacturer': makers[0] if len(makers) == 1 else None, 'makers': makers,
                'listed': sorted({h['mpn'] for h in hits})[:6], 'description': best.get('description'),
                'datasheet_url': best.get('datasheet_url'), 'sources': ['digikey']}

    # ---- apply --------------------------------------------------------------------------
    def apply(self, options):
        verdicts = load_verdicts()
        dry = options['dry_run']
        done = {'standard': [0, 0], 'confirmed': [0, 0], 'junk': [0, 0]}
        touched_products, touched_components = set(), set()
        with transaction.atomic():
            for name, component_id, population, n in work():
                kind = classify(name, population, verdicts)
                if kind not in done:
                    continue
                source = Component.objects.get(pk=component_id)
                rows = (ProductComponent.objects.filter(component=source, import_source__startswith=TAG, needs_review=True)
                        if population == 'labels' else ProductComponent.objects.filter(component=source))
                touched_products |= set(rows.values_list('product_id', flat=True))
                touched_components.add(source.pk)
                target = None
                if kind == 'junk':
                    rows.delete()
                else:
                    verdict = verdicts.get(name) or {}
                    target = self.target(name, population, source, kind, verdict)
                    touched_components.add(target.pk)
                    at = ' and '.join(verdict.get('sources') or ['a distributor'])
                    if verdict.get('status') == 'prefix':
                        at += ' as the family ' + ', '.join(verdict.get('listed') or [])
                        if not verdict.get('manufacturer') and not one_maker(verdict.get('makers') or []):
                            at += ' (made by ' + ', '.join(verdict.get('makers') or []) + ')'
                    note = (STANDARD_NOTE if kind == 'standard'
                            else (CONFIRMED_NOTE if population == 'labels' else CONFIRMED_LINE_NOTE).format(source=at))
                    for row in rows:
                        row.component = target
                        if row.needs_review or UNCONFIRMED in (row.notes or '') or UNCONFIRMED_LINE in (row.notes or ''):
                            row.needs_review = False
                            row.notes = self.renote(row.notes, note)
                        row.save(update_fields=['component', 'needs_review', 'notes'])
                if (target is None or target.pk != source.pk) and not ProductComponent.objects.filter(component=source).exists():
                    touched_components.discard(source.pk)
                    source.delete()               # its rows moved to an existing part, or were junk
                done[kind][0] += 1
                done[kind][1] += n
            refresh_usage_counts(touched_components)
            for product in Product.objects.filter(pk__in=touched_products):
                product.update_component_count()
            self.stdout.write(f'{"DRY RUN (rolled back) - " if dry else ""}standard {done["standard"][0]} parts / {done["standard"][1]} rows, '
                              f'confirmed {done["confirmed"][0]} / {done["confirmed"][1]}, junk removed {done["junk"][0]} / {done["junk"][1]}, '
                              f'products recounted {len(touched_products)}')
            if dry:
                transaction.set_rollback(True)

    @staticmethod
    def target(name, population, source, kind, verdict):
        """The component the rows move to: an existing part of the right maker and number, or
        the source itself renamed. The old name survives in alternative_part_numbers; a line
        name also stays as the description, since it is the factory's own words."""
        package = chip_labels.split(name)[1] if population == 'labels' else None
        if kind == 'standard':
            maker, mpn, description = 'Generic', chip_labels.standard_from_label(name), source.description
            if (description or '').startswith(name):
                description = mpn + description[len(name):]      # 'NPN-3904LT1-S-SOT23 (transistor)' -> 'MMBT3904LT1 (transistor)'
        else:
            maker = (canonical_maker(verdict.get('manufacturer') or '') or verdict.get('manufacturer')
                     or one_maker(verdict.get('makers') or []) or 'Generic')
            mpn = verdict.get('candidate') if verdict.get('status') == 'prefix' else (verdict.get('mpn') or verdict.get('candidate'))
            description = source.description if population == 'lines' else (verdict.get('description') or source.description)
        # an existing part of that number under the maker's old or new name is the same part: keep it
        family = next((f for f in FAMILIES if maker in f), (maker,))
        existing = (Component.objects.filter(part_number__iexact=mpn, manufacturer__in=family).exclude(pk=source.pk)
                    .order_by('-usage_count').first())
        target = existing or source
        changed = []
        if target is source:
            source.manufacturer, source.part_number = maker, mpn
            changed += ['manufacturer', 'part_number']
        if name != target.part_number and name not in (target.alternative_part_numbers or []):
            target.alternative_part_numbers = [*(target.alternative_part_numbers or []), name]
            changed.append('alternative_part_numbers')
        if description and (target is source or not target.description) and target.description != description:
            target.description = description
            changed.append('description')
        if package and not target.package_type:
            target.package_type = package
            changed.append('package_type')
        if verdict.get('datasheet_url') and not target.datasheet_url:
            target.datasheet_url = verdict['datasheet_url']
            changed.append('datasheet_url')
        if changed:
            target.save(update_fields=sorted(set(changed)))
        return target

    @staticmethod
    def renote(notes, note):
        text = notes or ''
        for marker in (UNCONFIRMED, UNCONFIRMED_LINE):
            if marker in text:
                head = text.partition(f'; {marker}')[0] if f'; {marker}' in text else ''
                return f'{head}; {note}' if head else note
        return f'{text}; {note}' if text else note
