"""
Fill in component ratings (value, voltage, power, current, tolerance, dielectric,
...), package and type from descriptions and part numbers, and give BOM-imported
components their own factory line as description.

    manage.py refresh_component_specs [--lines FILE] [--types] [--dry-run] [--report FILE]

--lines   site_export_lines.json from the Norway BOM export: every exported
          part's own BOM line(s). A component whose description is machine-made
          (a factory line, possibly another part's, or the "Factory-approved
          alternate to ..." placeholder) gets its own line, without the factory's
          markers, as description.
--types   also correct component types the description or part number contradicts
          (a resistor typed 'ic', a chassis typed 'capacitor').
--report  TSV of every change and every conflict left for a person.

Stored ratings are never overwritten: where the text or part number disagrees
with a stored value, the report says so. Where a part's own lines disagree on
a rating (its value, current, dielectric, package...) and its part number can't
settle it, that rating isn't filled, and an importer's earlier pick is taken out.
Idempotent.
"""
import collections
import csv
import json
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.components.makers import canonical_part
from apps.components.models import Component, ProductComponent
from apps.components.spec_fill import plan
from apps.components.spec_parse import (VALUE_KEYS, clean_bom_text, decode_mpn, derive, ic_package, kind_of,
                                        parse_description)
from apps.products.import_text import bom_component_type, clean_description, clean_text
from utils.cache import clear_page_cache

PLACEHOLDER = 'Factory-approved alternate'
# parts lists include the mechanical parts too; whatever their position said, they are 'other'
MECHANICAL = re.compile(
    r'^(?:[\w-]*\s)?(SCREW|NUT|WASHER|SPRING WASHERS?|PLAIN WASHER|C-CLIP|CLIP|DOOR|BAG|LABEL|BRACKET|KNOB|BEZEL|'
    r'(?:TOP |BASE |BOTTOM |REAR |FRONT |SIDE )?COVER|CASE|HOLDER|CUSHION|TAPE|SHEET|SPACER|BOSS|CHASSIS|'
    r'(?:FRONT |REAR )?PANEL|LEVER|SPRING|PACKING|BOX|MANUAL|FOOT|FOOT PAD|RUBBER|DECO|WINDOW|GASKET|SPONGE|'
    r'HINGE|STAND|FILM|INSULATOR|PAD|HEAT CONDUCTIVE PAD|SHIELDING BOX|ASSY\b(?! PCB)|CLAMPER|BUTTON|'
    r'(?:POWER |DUO |\dP INPUT )BUTTON|LENS|(?:\w+ )*KNOB BEZEL|LED LENS BEZEL)\b', re.I)
PASSIVE = {'resistor', 'capacitor', 'inductor', 'ferrite', 'crystal', 'thermistor', 'fuse'}
# current parts suggested for a generic BOM line were mislabelled as factory alternates
EQUIVALENT_OF_GENERIC = PLACEHOLDER + ' to Generic '


def machine_made(desc, all_lines):
    """A description an importer wrote (a factory BOM line or the alternate placeholder),
    as opposed to one a person wrote or a datasheet supplied."""
    d = desc or ''
    return (d.startswith(PLACEHOLDER) or d in all_lines or clean_bom_text(d) != re.sub(r'\s+', ' ', d.strip()))


SERVICE_NOTE = re.compile(r'^Service manual parts list, pages? [\d, ]+: ')
def _has_value(specs):
    return any(k in specs for k in VALUE_KEYS)


MAJORITY = 0.9      # share of a part's placements whose lines must agree for their rating to stand


def own_line(lines):
    """(text, disagree, majority): the part's most used own line that gives a value, else its most
    used line (a bare 'R-CHIP' says less than 'R-CHIP;2Kohm,5%,...'); the ratings its lines give
    different values for ('package' when they name different chip sizes) - a factory BOM can
    list one part as 400mA and as 600mA; and, of those, the ones that nearly all of the part's
    placements agree on, with that value (52 lines at 10A, one at 6A: 10A)."""
    seen, best = {}, None
    for text, count in lines:
        found = derive('', '', text)        # some manuals give the vendor part number: 'CL10A226MP8NUNE'
        specs, package = found['specs'], found['package']
        if best is None and any(k in specs for k in VALUE_KEYS):
            best = text
        if package and re.fullmatch(r'\d{4}', package):
            specs = {**specs, 'package': package}       # case sizes; a can's 8x11 vs 8x11.5 is the same part
        for key, value in specs.items():
            value = round(value, 6) if isinstance(value, float) else value
            seen.setdefault(key, collections.Counter())[value] += count
    disagree, majority = [], {}
    for key, values in seen.items():
        if len(values) > 1:
            disagree.append(key)
            value, count = values.most_common(1)[0]
            if count >= MAJORITY * sum(values.values()):
                majority[key] = value
    return best or lines[0][0], sorted(disagree), majority


class Command(BaseCommand):
    help = 'Fill component ratings, package and type from descriptions and part numbers'

    def add_arguments(self, parser):
        parser.add_argument('--lines', help='site_export_lines.json (own BOM line per part)')
        parser.add_argument('--types', action='store_true', help='also correct contradicted component types')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--report', help='write a TSV of changes and conflicts')

    def handle(self, *args, **options):
        lines = {}
        if options['lines']:
            with open(options['lines'], encoding='utf-8') as fh:
                for key, found in json.load(fh).items():
                    # keyed as the export spelled the maker; the site may spell it otherwise
                    maker, part = canonical_part(*key.split('|', 1))
                    lines.setdefault(f'{maker.upper()}|{part.upper()}', []).extend(found)
        # a service manual's line, kept in each placement's notes: one manual lists 2007-000137 as
        # 'R-CHIP', another as 'R-CHIP;2Kohm,5%,1/16W,TP,1005'
        manual_lines = collections.defaultdict(collections.Counter)
        for maker, part, notes in ProductComponent.objects.filter(notes__startswith='Service manual parts list') \
                .values_list('component__manufacturer', 'component__part_number', 'notes'):
            line = SERVICE_NOTE.sub('', notes)
            if line:
                manual_lines[f'{maker.upper()}|{part.upper()}'][line] += 1
        manual_only = set(manual_lines) - set(lines)
        for key, found in manual_lines.items():
            lines.setdefault(key, []).extend([text, n] for text, n in found.items())
        for found in lines.values():
            found.sort(key=lambda line: -line[1])           # most used first
        all_lines = {t for v in lines.values() for t, _ in v}
        # components an importer wrote: placed by an import, or a suggested equivalent of a generic part
        imported = set(ProductComponent.objects.exclude(import_source='').values_list('component_id', flat=True))
        imported |= set(Component.objects.filter(cross_references__manufacturer='Generic')
                        .values_list('pk', flat=True))
        counts = dict.fromkeys(('components', 'descriptions', 'specs', 'corrected', 'removed', 'packages', 'types',
                                'conflicts', 'disputed'), 0)
        rows = []
        with transaction.atomic():
            for comp in Component.objects.order_by('manufacturer', 'part_number').iterator(chunk_size=500):
                counts['components'] += 1
                change = self.refresh(comp, lines, all_lines, options['types'], imported, manual_only)
                if not change:
                    continue
                for key in ('descriptions', 'specs', 'corrected', 'removed', 'packages', 'types', 'conflicts',
                            'disputed'):
                    counts[key] += bool(change.get(key))
                rows.append(change)
                if change['fields'] and not options['dry_run']:
                    comp.save(update_fields=change['fields'])
            if options['dry_run']:
                transaction.set_rollback(True)
        if not options['dry_run'] and any(r['fields'] for r in rows):
            clear_page_cache()
        if options['report']:
            with open(options['report'], 'w', newline='', encoding='utf-8') as fh:
                w = csv.writer(fh, delimiter='\t')
                w.writerow(['id', 'manufacturer', 'part_number', 'type', 'new type', 'description', 'new description',
                            'specs added', 'corrected by part number', 'package', 'conflicts (stored vs found)',
                            'line vs part number (part number used)', 'disputed value (not filled)',
                            'removed (disputed, import-written)', 'source text'])
                for r in rows:
                    w.writerow([r['id'], r['manufacturer'], r['part_number'], r['type'], r.get('types', ''),
                                r['description'], r.get('descriptions', ''), json.dumps(r.get('specs', {})),
                                json.dumps(r.get('corrected') or {}), r.get('packages', ''),
                                ','.join(r.get('conflicts', [])), ','.join(r.get('overridden', [])),
                                ','.join(r.get('disputed', [])), ','.join(r.get('removed', [])), r['text']])
        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(prefix + ', '.join(f'{k}: {v}' for k, v in counts.items())))

    @staticmethod
    def refresh(comp, lines, all_lines, fix_types, imported, manual_only=frozenset()):
        """Changes for one component (applied to `comp`, not saved), or None."""
        if comp.manufacturer == 'Generic':
            return None         # generic passives carry full specs
        if (comp.specifications or {}).get('source') == 'datasheet':
            # datasheet title-page text isn't a parts line: no ratings from it. The type is read from
            # the whole text, while it's there (import_datasheets types new parts the same way), then
            # the description becomes just the title.
            out = {'id': str(comp.pk), 'manufacturer': comp.manufacturer, 'part_number': comp.part_number,
                   'type': comp.component_type, 'description': comp.description, 'text': comp.description,
                   'fields': []}
            title = clean_description(comp.description, part_number=comp.part_number)
            new_type = datasheet_type(comp) if fix_types and title != comp.description else None
            if new_type and new_type != comp.component_type:
                out['types'] = comp.component_type = new_type
                out['fields'].append('component_type')
            if title != comp.description:
                out['descriptions'] = comp.description = title
                out['fields'].append('description')
            return out if out['fields'] else None
        out = {'id': str(comp.pk), 'manufacturer': comp.manufacturer, 'part_number': comp.part_number,
               'type': comp.component_type, 'description': comp.description, 'fields': []}
        key = f'{comp.manufacturer.upper()}|{comp.part_number.upper()}'
        mine = lines.get(key)
        made = machine_made(comp.description, all_lines)
        text, disagree, majority = own_line(mine) if mine else (comp.description, [], {})
        decoded = decode_mpn(comp.manufacturer, comp.part_number)
        if decoded:     # the part number settles what it encodes
            disagree = [k for k in disagree if k not in decoded[1] and not (k == 'package' and decoded[2])]
        majority = {k: v for k, v in majority.items() if k in disagree}
        disagree = [k for k in disagree if k not in majority]
        if not mine and comp.description.startswith((PLACEHOLDER, 'Current equivalent of')):
            text = ''           # these name another part's line: nothing in them is about this one
        out['text'] = text
        new = None
        if made and mine and key in manual_only:
            # manuals word one part differently ('PESD5V0L5UV', 'DIODE-TVS'): a description is only
            # replaced by a line that gives the values it lacks
            if _has_value(parse_description(text)[1]) and not _has_value(parse_description(comp.description)[1]):
                new = clean_bom_text(clean_text(text))
        elif made and mine:
            new = clean_bom_text(clean_text(text))
        elif made and comp.description.startswith(EQUIVALENT_OF_GENERIC):
            new = 'Current equivalent of ' + comp.description[len(PLACEHOLDER + ' to '):].split(' (')[0]
        elif made and not comp.description.startswith(PLACEHOLDER):
            new = clean_bom_text(clean_text(comp.description))
        if new and new != comp.description:
            out['descriptions'] = new
            comp.description = new
            out['fields'].append('description')

        # an alternate placed nowhere still had its ratings written by the import from its own line
        import_written = comp.pk in imported or made or bool(mine) and comp.description in {
            clean_bom_text(clean_text(t)) for t, _ in mine}
        p = plan(comp, text, trust_part_number=import_written)
        added = p['added']
        rating_disagree = [k for k in disagree if k != 'package']
        if import_written and (p['disputed'] or rating_disagree):
            # an importer stored a value its own line and part number disagree on, or one of the
            # part's own lines that the others contradict: take it out
            removed = [k for k in p['disputed'] + rating_disagree if k in (comp.specifications or {})]
            if removed:
                comp.specifications = {k: v for k, v in comp.specifications.items() if k not in removed}
                p['specs'] = {k: v for k, v in p['specs'].items() if k not in removed}
                p['conflict'] = [k for k in p['conflict'] if k not in removed]
                out['removed'] = removed
                out['fields'].append('specifications')
        if disagree:
            added = [k for k in added if k not in disagree]          # its own lines disagree: not filled
            p['disputed'] = sorted(set(p['disputed']) | {f'{k} (own lines)' for k in disagree})
        for key, value in majority.items():
            if key == 'package':
                if not comp.package_type or import_written:
                    p['package'] = value
                    p['conflict'] = [k for k in p['conflict'] if k != 'package']
            elif key in p['specs'] and p['specs'][key] != value and (import_written or key in added):
                # the stored or parsed value came from a line nearly all the others contradict
                p['specs'][key] = value
                p['conflict'] = [k for k in p['conflict'] if k != key]
                if key not in added:
                    p['corrected'].append(key)
        if added or p['corrected']:
            keep = set(comp.specifications or {}) - {'tolerance_pct'}
            comp.specifications = {k: v for k, v in p['specs'].items() if k in added or k in keep}
            out['specs'] = {k: comp.specifications[k] for k in added if k in comp.specifications}
            out['corrected'] = {k: comp.specifications[k] for k in p['corrected']}
            if 'specifications' not in out['fields']:
                out['fields'].append('specifications')
        package = p['package']
        if not package and text and comp.component_type not in PASSIVE:
            package = ic_package(text) or ''
        if 'package' in disagree:
            package = ''
            if import_written and comp.package_type:
                out['removed'] = out.get('removed', []) + ['package']
                comp.package_type = ''
                out['fields'].append('package_type')
            p['conflict'] = [k for k in p['conflict'] if k != 'package']
        if 'package' in majority and package != comp.package_type:
            out['packages'] = comp.package_type = package
            out['fields'].append('package_type')
        elif package and package != comp.package_type and not comp.package_type:
            out['packages'] = package
            comp.package_type = package
            out['fields'].append('package_type')
        out['conflicts'], out['overridden'], out['disputed'] = p['conflict'], p['overridden'], p['disputed']
        if fix_types:
            new_type = proposed_type(comp, p, text, bom_line=bool(mine) or made)
            if new_type and new_type != comp.component_type:
                out['types'] = new_type
                comp.component_type = new_type
                out['fields'].append('component_type')
        if out['fields'] or out['conflicts'] or out['disputed']:
            return out
        return None


# Samsung service codes are numbered by family; the family decides the type when the parts list
# gives only a part number, and 'IC-...' lines are integrated circuits whatever their position said
SAMSUNG_FAMILY = [(r'^020[0-9]-', 'other'), (r'^040[1-7]-', 'diode'), (r'^050[1-4]-', 'transistor'),
                  (r'^0505-', 'mosfet'), (r'^0601-', 'led'), (r'^1404-', 'thermistor'), (r'^2007-', 'resistor'),
                  (r'^(2203|2402)-', 'capacitor'), (r'^270[34]-', 'inductor'), (r'^3301-', 'ferrite'),
                  (r'^280[15]-', 'crystal'), (r'^29(0[1-9]|1[01])-', 'balun'), (r'^37(0[1-9]|1[0-9]|2[0-2])-', 'connector'),
                  (r'^(60\d\d|6502|6902)-', 'other')]
SAMSUNG_IC = [(r'EEPROM|FLASH|[SD]?RAM\b|MEMORY', 'eeprom'), (r'MICROCONTROLLER|MICROPROCESSOR|MICOM', 'mcu'),
              (r'POSI\.|NEGA\.|DC[-/]DC|VOL\. ?REG|SWITCH REG|REGULATOR|LDO', 'regulator'), (r'OP\.? ?AMP', 'opamp'),
              (r'SENSOR', 'sensor')]
IC_TYPES = {'ic', 'eeprom', 'mcu', 'regulator', 'opamp'}


def samsung_type(comp, line):
    if comp.manufacturer != 'Samsung' or not re.match(r'\d{4}-\d{6}$', comp.part_number):
        return None
    u = line.upper()
    if u.startswith('IC-'):
        if comp.component_type in IC_TYPES | {'sensor'}:
            return None
        return next((t for pattern, t in SAMSUNG_IC if re.search(pattern, u)), 'ic')
    if re.fullmatch(r'[A-Z0-9][A-Z0-9-]{4,24}', u) and re.search(r'\d', u):      # just a part number
        return next((t for pattern, t in SAMSUNG_FAMILY if re.match(pattern, comp.part_number)), None)
    if re.match(r'^0202-', comp.part_number):                                   # solder, flux, shorting wire
        return 'other'
    return None


# Components made from a datasheet were typed by any type word on its title page ('...Buck
# MOSFET Driver' became a mosfet). Part-number conventions decide first, then the title's
# function: an IC phrase anywhere makes it an IC, otherwise the discrete device it names.
DATASHEET_PN = [
    (r'^2S[ABCD]\d', 'transistor'), (r'^2S[JK]\d', 'mosfet'), (r'^1S[SVR]?\d', 'diode'),
    (r'^(FD[SDNPUBGHMCZY]|FQ[PDAUBT]|NDS|NDT|NDP|NDB|SI\d{4}[A-Z]*DY)', 'mosfet'),
    (r'^P\d{2,4}[NP]\d', 'mosfet'),                          # Niko-Sem power MOSFETs
]
DATASHEET_IC = [
    ('ic', r'(MOSFET|GATE|LED|FET)\s+(SMART\s+)?DRIVER'),
    ('eeprom', r'EEPROM|FLASH MEMORY|SERIAL FLASH|\bSRAM\b|\bDRAM\b'),
    ('mcu', r'MICROCONTROLLER|\bMCU\b'),
    ('opamp', r'OPERATIONAL AMPLIFIER|\bOP[ -]?AMPS?\b|COMPARATOR'),
    ('regulator', r'REGULATOR|\bLDO\b|DC[/-]DC|STEP[ -](UP|DOWN)|BUCK|BOOST|\bPWM\b|VRM|SWITCHING CONTROLLER|'
                  r'POWER SUPPLY CONTROLLER|CONVERTER|PMIC|POWER MANAGEMENT|CHARGE PUMP'),
    ('ic', r'DRIVER|CONTROLLER|CHARGER|MONITOR|CODEC|COUNTER|\bPLL\b|PHASE[ -]LOCKED|CLOCK|GENERATOR|BUFFER|'
           r'\bGATES?\b|FLIP[ -]FLOP|DECODER|ENCODER|MULTIPLEXER|TRANSCEIVER|INTERFACE|SENSOR|AMPLIFIER|'
           r'SUPERVISOR|RESET|SWITCH(?!ING (APPLICATIONS|TRANSISTOR))|LOGIC(?! LEVEL)|\bASIC\b|SUPER I/O|AUDIO|'
           r'VIDEO|TIMER|REFERENCE|PROCESSOR|BRIDGE|CHIPSET|USB|ETHERNET|PHY|ADC|DAC\b|SHIFT REGISTER|LATCH|'
           r'INVERTER|NAND|HUB|MODEM|RF SYSTEM|TRANSMITTER|RECEIVER|MULTIPLIER|SYNTHESIZER'),
]
DATASHEET_DISCRETE = [
    ('mosfet', r'MOSFET|FIELD[ -]EFFECT|\bFET\b|MOS TYPE'), ('transistor', r'TRANSISTOR|DARLINGTON|\bIGBT\b'),
    ('diode', r'DIODE|RECTIFIER|ZENER|SCHOTTKY|\bTVS\b'),
]
DATASHEET_MAKER = {'Niko Semiconductor': 'mosfet'}          # makes power MOSFETs only
# part-number families that are integrated circuits only: never typed as a discrete or a passive
IC_FAMILY = re.compile(r'^(MAX|ISL|HIP|RT\d|SC\d|ICS|TPS|BQ|SN[57]4|TL\d|TLV|MC1\d|NCP|ADP|ADM|APW|APL|UP\d|'
                       r'G\d{3}|MT\d|W8\d|IT8|F7\d|ALC|LTC|LT\d|FAN|74|CD4|NC7|LM\d|TPA|SI91|SC\d|AAT|AME|AP\d{4})')


def datasheet_type(comp):
    """Type for a component made from a datasheet, from its part number and title text: a
    part-number convention, else the function the title names first, else the discrete device."""
    pn, title = comp.part_number.upper(), (comp.description or '').upper()
    for pattern, kind in DATASHEET_PN:
        if re.match(pattern, pn):
            if kind == 'mosfet' and re.search(r'JUNCTION|\bJFET\b', title):
                return 'transistor'
            return kind
    if comp.manufacturer in DATASHEET_MAKER and not re.search(r'DRIVER|CONTROLLER|REGULATOR', title):
        return DATASHEET_MAKER[comp.manufacturer]
    if IC_FAMILY.match(pn):
        kind = _datasheet_function(title)
        return kind if kind in IC_TYPES else 'ic'
    return _datasheet_function(title)


def _datasheet_function(title):
    # 'Silicon Transistor ... Driver Applications' names its uses, not its function
    title_fn = re.split(r'\bAPPLICATIONS?\b', title)[0] if re.search(r'TRANSISTOR|MOSFET|DIODE|\bFET\b', title) else title
    power = re.search(r'\bPWM\b|BUCK|BOOST|VRM|\bVR\b|PHASE|STEP[ -](UP|DOWN)|DC[/-]DC|POWER[ -]SUPPLY|LINEAR POWER',
                      title_fn)
    if re.search(r'FAN CONTROLLER|THERMAL (MONITOR|CONTROLLER)|TEMPERATURE (MONITOR|SENSOR)', title_fn):
        return 'ic'                                       # hardware monitors: their PWM drives a fan
    if re.search(r'CONTROLLER', title_fn) and power:
        return 'regulator'                                # a switching/linear regulator's controller
    if re.search(DATASHEET_IC[0][1], title_fn):
        return 'ic'                                       # gate/MOSFET drivers, whatever else is named
    first = None
    for kind, pattern in DATASHEET_IC:
        m = re.search(pattern, title_fn)
        if m and (first is None or m.start() < first[0]):
            first = (m.start(), kind)
    discrete = next(((m.start(), kind) for kind, pattern in DATASHEET_DISCRETE
                     if (m := re.search(pattern, title_fn))), None)
    if first and not (discrete and discrete[0] < first[0] and not re.search(
            r'DRIVER|CONTROLLER|REGULATOR|CONVERTER|CHARGER', title_fn)):
        return first[1]
    return discrete[1] if discrete else None


def proposed_type(comp, p, text, bom_line=False):
    """Type the evidence supports, or None. A decoded part number is certain; a description
    counts when it starts with the part's kind ('R-CHIP;...', 'MLCC ...') or names the kind and
    gives a value of that kind ('Metal film chip resistor, 1/4W, 10 kOhm'). bom_line: `text` is
    the part's factory BOM line, whose head names its kind ('ZIF 939P uPGA', 'HEADER 2X5P')."""
    if decode_mpn(comp.manufacturer, comp.part_number):
        return p['type']
    line = clean_bom_text(text or comp.description or '')
    family = samsung_type(comp, line)
    if family:
        return family
    if bom_line and comp.component_type == 'ic':
        # an earlier import gave the alternates of sockets, slots and headers the type 'ic'
        kind = bom_component_type(line)
        if kind and kind not in IC_TYPES | {'crystal'}:
            return kind
    kind = p['derived']['kind']
    if re.search(r'\bSENSOR\b', line, re.I) and comp.component_type in PASSIVE | {'ic', 'other'}:
        return 'sensor'                                  # 'ASSY SENSOR PRESSURE'
    if re.search(r'\bS/W\b', line) and comp.component_type in PASSIVE | {'other'}:
        return 'switch'                                  # 'DOOR-LOCK S/W'
    if not kind_of(line) and not re.search(r'\bS/W\b', line) and MECHANICAL.match(line) and comp.component_type in PASSIVE | {
            'transformer', 'diode', 'connector', 'switch', 'led', 'ic', 'transistor'}:
        return 'other'
    if not kind or not p['type']:
        return None
    if kind_of(line, head_only=True) == kind:
        return p['type']
    # prose that merely mentions the kind ('NPN digital transistor, built-in bias resistors
    # (R1=10k)') only retypes a part filed as unknown or as another passive
    has_value = any(k in p['derived']['specs'] for k in VALUE_KEYS)
    if has_value and comp.component_type in PASSIVE | {'ic', 'other'}:
        return p['type']
    return None
