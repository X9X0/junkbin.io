"""
Equivalent-part search for generic components.

A BOM line like "CAP 10nF 200V" or "RES 10K 5% 1/4W" is stored as a Component
with manufacturer "Generic" and the spec string as its part number. No
distributor sells a part by that name, so the exact-match lookup (lookup.py)
can never answer for it. This module asks DigiKey's keyword search with a
spec-style query instead, keeps the hits whose ratings fit the line (same
value, voltage and power at least as high, tolerance no wider) and ranks
them by how close they are and whether they are in stock.

Results are cached in ExternalPartSearch under the query text, so the
thousands of generic rows that share a spec string share one API call,
and the cached row lets external-add turn a hit into a catalogue part.

mode(component) says which lookup a component gets:
    "exact"        a maker's part number: lookup.lookup_part
    "equivalents"  a generic line with a value: search() here
    "not_stocked"  valves, transformers, speakers: nothing to ask
"""
import logging
import re
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from .distributors import get_digikey
from .external_search import CACHE_DAYS, DIGIKEY_RESERVE, SearchUnavailable, digikey_keyword
from .models import ExternalPartSearch
from .spec_fill import _comparable
from .spec_parse import SITE_TYPE, parse_description

logger = logging.getLogger(__name__)

MAX_RESULTS = 8
KEYWORD_LIMIT = 25
VALUE_SLACK = 0.02           # a hit whose value is within 2% is the same value (E-series rounding)

# component types no distributor on the site stocks: say so instead of "no results"
NEVER_STOCKED = {'vacuum_tube': 'Vacuum tubes', 'transformer': 'Transformers', 'speaker': 'Speakers'}

# type -> (DigiKey description prefix, value key, value formatter)
KINDS = {
    'resistor': ('RES', 'resistance_ohm', 'ohms'),
    'thermistor': ('THERMISTOR NTC', 'resistance_ohm', 'ohms'),
    'potentiometer': ('POT', 'resistance_ohm', 'ohms'),
    'capacitor': ('CAP', 'capacitance_pf', 'farads'),
    'inductor': ('IND', 'inductance_uh', 'henries'),
    'ferrite': ('FERRITE BEAD', 'impedance_ohm', 'ohms'),
    'fuse': ('FUSE', 'current_a', 'amps'),
    'crystal': ('CRYSTAL', 'frequency_mhz', 'mhz'),
}
DIELECTRIC_WORDS = {'electrolytic': 'ALUM', 'tantalum': 'TANT', 'film': 'FILM', 'ceramic': 'CER', 'mica': 'MICA'}
FUSE_SPEED = {'slow': 'SLOW BLOW', 'fast': 'FAST ACTING'}
WATTS = {1 / 20: '1/20W', 1 / 16: '1/16W', 1 / 10: '1/10W', 1 / 8: '1/8W', 1 / 4: '1/4W', 1 / 2: '1/2W', 3 / 4: '3/4W'}


def mode(component):
    """'exact', 'equivalents' or 'not_stocked' (see module docstring)."""
    if component.component_type in NEVER_STOCKED:
        return 'not_stocked'
    if component.manufacturer == 'Generic' and query_for(component):
        return 'equivalents'
    return 'exact'


# a word that is a package or a rating, not a part number: PDIP-8, TO-92, SOP-8, 2.54MM, 16V, 1/4W
NOT_A_PART = re.compile(r'^(?:PLCC|SOT|SOD|SOP|SSOP|TSSOP|TSOP|MSOP|QFN|DFN|QFP|LQFP|TQFP|BGA|DPAK|D2PAK|TO|SOIC|SO|DIP|PDIP|'
                        r'SIP|SMA|SMB|SMC|SMD|DO)-?\d*[A-Z]?$|^[\d./]+(?:MM|V|W|A|MA|MHZ|KHZ|OHM|K|M|UF|NF|PF|UH|%|P|PIN)$', re.I)
# a word of letters, digits, '.' or '-' ('/' splits MAKER/PART); part-number shaped when five or
# more long with a letter and two digits
WORD = re.compile(r'(?<![A-Z0-9])[A-Z0-9][A-Z0-9.-]{4,39}(?![A-Z0-9])', re.I)
MAX_EXACT_TRIES = 3


def part_shaped(word):
    return (re.search(r'[A-Z]', word, re.I) is not None and len(re.findall(r'\d', word)) >= 2
            and not NOT_A_PART.match(word))


def exact_queries(component):
    """[(part number, maker or None), ...] for the distributors' exact-match lookup, best first.

    A maker's part is asked for as it is. A Generic part is asked for without a maker filter
    ('Generic' never matches a distributor's maker name, so a filtered lookup of 'Generic
    2N3904' could never answer). When its name is a whole BOM line ('FLASH MXIC
    MX25L8005PC-15G 8M SPI PDIP-8'), the part-number-shaped words in it are tried instead,
    longest first (MX25L8005PC-15G); packages and ratings (PDIP-8, 16V) are not words to try,
    and a maker abbreviation before the word (MXIC) is kept for display, not as a filter."""
    from .makers import canonical_maker
    name = (component.part_number or '').strip()
    if component.manufacturer != 'Generic':
        return [(name, component.manufacturer)]
    words = [w for w in WORD.findall(name) if part_shaped(w)]
    if ' ' not in name or not words:
        return [(name, None)]
    queries = []
    for word in sorted(dict.fromkeys(words), key=len, reverse=True)[:MAX_EXACT_TRIES]:
        before = re.search(r'([A-Z][A-Z.&-]{1,24})\s*/\s*' + re.escape(word) + r'(?![A-Z0-9])|([A-Z][A-Z.&-]{1,24})\s+' + re.escape(word) + r'(?![A-Z0-9])',
                           name, re.I)
        maker = None
        if before:
            printed = before.group(1) or before.group(2)
            canonical = canonical_maker(printed)
            if canonical != printed or before.group(1):      # a known abbreviation, or MAKER/PART
                maker = canonical
        queries.append((word, maker))
    return queries


def _ohms(v):
    if v >= 1e6:
        return f'{v / 1e6:g}M'
    if v >= 1e3:
        return f'{v / 1e3:g}K'
    return f'{v:g}'


def _farads(pf):
    if pf >= 1e6:
        return f'{pf / 1e6:g}UF'
    if pf >= 1e3:
        return f'{pf / 1e3:g}NF'
    return f'{pf:g}PF'


def _henries(uh):
    if uh >= 1e3:
        return f'{uh / 1e3:g}MH'
    if uh < 1:
        return f'{uh * 1e3:g}NH'
    return f'{uh:g}UH'


FORMAT = {'ohms': _ohms, 'farads': _farads, 'henries': _henries,
          'amps': lambda a: f'{a:g}A', 'mhz': lambda m: f'{m:g}MHZ'}


def _tolerance_pct(text):
    m = re.search(r'(\d+(?:\.\d+)?)\s*%', str(text or ''))
    return float(m.group(1)) if m else None


def query_for(component):
    """DigiKey keyword text for a generic line, or '' when the line has no value to search by."""
    kind = KINDS.get(component.component_type)
    if not kind:
        return ''
    prefix, value_key, fmt = kind
    specs = _comparable(component.specifications or {})
    value = specs.get(value_key)
    if not isinstance(value, (int, float)) or value <= 0:
        return ''
    words = [prefix, FORMAT[fmt](value)]
    if fmt == 'ohms':
        words.append('OHM')
    if component.component_type == 'fuse':
        words.append(FUSE_SPEED.get(str(specs.get('speed', '')).lower(), ''))
    tol = _tolerance_pct(specs.get('tolerance'))
    if tol is not None and component.component_type != 'capacitor':
        words.append(f'{tol:g}%')
    if isinstance(specs.get('voltage_v'), (int, float)) and component.component_type in ('capacitor', 'fuse'):
        words.append(f'{specs["voltage_v"]:g}V')
    if isinstance(specs.get('power_w'), (int, float)) and component.component_type in ('resistor', 'potentiometer'):
        w = specs['power_w']
        words.append(next((t for k, t in WATTS.items() if abs(k - w) < 1e-9), f'{w:g}W'))
    if component.component_type == 'capacitor':
        d = str(specs.get('dielectric', '')).lower()
        words.append(DIELECTRIC_WORDS.get(d, d.upper() if re.fullmatch(r'[a-z0-9]{2,5}', d) else ''))
    package = component.package_type or specs.get('size_on_bom') or ''
    if re.fullmatch(r'\d{4}', str(package)):
        words.append(str(package))
    return ' '.join(w for w in words if w)[:60]


def search(component):
    """(candidates, from_cache) for a generic component. Raises SearchUnavailable when
    DigiKey cannot be asked (reserve spent, not configured, outage)."""
    query = query_for(component)
    if not query:
        return [], False
    cached = ExternalPartSearch.objects.filter(query=query).first()
    if cached and cached.fetched_at > timezone.now() - timedelta(days=CACHE_DAYS):
        ExternalPartSearch.objects.filter(pk=cached.pk).update(search_count=cached.search_count + 1)
        return cached.results, True

    digikey = get_digikey()
    if not digikey.is_configured or cache.get('digikey_remaining', 1000) <= DIGIKEY_RESERVE:
        raise SearchUnavailable('DigiKey search budget for today is used up')
    try:
        hits = digikey_keyword(digikey, query, limit=KEYWORD_LIMIT)
    except Exception as exc:
        logger.warning('DigiKey parametric search failed for %s: %s', query, exc)
        raise SearchUnavailable(f'DigiKey did not answer ({exc})')
    finally:
        if digikey.remaining is not None:
            cache.set('digikey_remaining', digikey.remaining, 6 * 3600)
    results = rank(hits, component)[:MAX_RESULTS]
    ExternalPartSearch.objects.update_or_create(
        query=query, defaults={'results': results, 'sources': ['digikey', 'parametric'], 'fetched_at': timezone.now(),
                               'search_count': (cached.search_count + 1) if cached else 1})
    return results, False


def rank(hits, component):
    """Hits that fit the generic line, best first, each with a 'fit' note. A hit whose
    parsed value, voltage or power rules it out is dropped; unknown ratings are kept
    but ranked below confirmed ones."""
    kept = {}
    for hit in hits:
        fit = judge(hit, component)
        if fit is None:
            continue
        row = {**{k: v for k, v in hit.items() if k != 'source'}, 'sources': [hit.get('source', 'digikey')], 'fit': fit}
        # one line per maker and description: packaging variants (reel, cut tape, automotive
        # grade) of the same part would otherwise fill the list; keep the best-stocked one
        key = (row.get('manufacturer', ''), re.sub(r'\s+', ' ', (row.get('description') or '').strip().lower()))
        if key not in kept or (row.get('stock') or 0) > (kept[key].get('stock') or 0):
            kept[key] = row
    return sorted(kept.values(), key=lambda h: (-h['fit']['score'], -(h.get('stock') or 0)))


def judge(hit, component):
    """{'score', 'notes', 'value'} for a hit against the component's ratings, or None to drop it."""
    kind_name, value_key, _ = KINDS[component.component_type]
    text = hit.get('description') or ''
    if component.component_type == 'potentiometer':
        text = 'RES ' + re.sub(r'^\s*POT\b', '', text)          # the parser knows resistors, not pots
    kind, specs, package = parse_description(text, component.component_type)
    if kind and SITE_TYPE.get(kind) not in (component.component_type, 'resistor' if component.component_type == 'potentiometer' else None):
        return None
    want = _comparable(component.specifications or {})
    score, notes, value_state = 0, [], 'unknown'

    target = want.get(value_key)
    got = specs.get(value_key)
    if isinstance(got, (int, float)) and target:
        if abs(got - target) / target > VALUE_SLACK:
            return None
        score += 3
        value_state = 'match'

    for key, higher_is_fine, label in (('voltage_v', True, 'V'), ('power_w', True, 'W'), ('current_a', None, 'A')):
        w, g = want.get(key), specs.get(key)
        if not isinstance(w, (int, float)) or not isinstance(g, (int, float)):
            continue
        if key == 'current_a' and component.component_type == 'fuse':
            if abs(g - w) / w > VALUE_SLACK:
                return None
            continue
        if g < w * (1 - VALUE_SLACK):
            return None                                     # under-rated: not a substitute
        score += 1
        if g > w * (1 + VALUE_SLACK):
            notes.append(f'{g:g} {label} (needs {w:g})')

    wt, gt = _tolerance_pct(want.get('tolerance')), _tolerance_pct(specs.get('tolerance'))
    if wt is not None and gt is not None:
        if gt <= wt:
            score += 1
        else:
            score -= 1
            notes.append(f'±{gt:g}% (wants ±{wt:g}%)')

    wd = str(want.get('dielectric', '')).lower()
    if wd:
        word = DIELECTRIC_WORDS.get(wd, wd.upper())
        if word and word in text.upper():
            score += 1
        elif word and any(w in text.upper() for w in DIELECTRIC_WORDS.values()):
            score -= 1

    wp = component.package_type or (component.specifications or {}).get('size_on_bom')
    if wp and package and str(wp).upper() == str(package).upper():
        score += 2
    if (hit.get('stock') or 0) > 0:
        score += 1
    if str(hit.get('status', '')).lower().startswith('obsolete'):
        score -= 2
    return {'score': score, 'notes': notes, 'value': value_state}


FAMILY_MIN_STEM = 6
FAMILY_MAX_CALLS = 5


def family_search(part_number):
    """(candidates, stem, from_cache) for a part no distributor lists any more: the parts
    whose numbers start with the longest stem of it that DigiKey still knows ('MX25L8005PC-15G'
    -> 'MX25L80' -> the MX25L8006E family). A repair needs the current family far more
    often than an exact match of a 20-year-old number. The stems are tried longest first,
    at most FAMILY_MAX_CALLS of them; a hit is kept only when its number starts with the
    stem, and ranked Active and in stock first. Raises SearchUnavailable like search()."""
    base = re.split(r'[-/ ]', (part_number or '').strip().upper(), 1)[0]
    # the number itself, then without its trailing letter group (a package or grade code:
    # MX25L8005PC -> MX25L8005), then one character shorter at a time
    core = re.sub(r'[A-Z]+$', '', base)
    stems = list(dict.fromkeys([base, core] + [core[:n] for n in range(len(core) - 1, FAMILY_MIN_STEM - 1, -1)]))
    stems = [s for s in stems if len(s) >= FAMILY_MIN_STEM]
    if not stems:
        return [], '', False
    cached = ExternalPartSearch.objects.filter(query__in=[f'FAMILY {s}' for s in stems],
                                              fetched_at__gt=timezone.now() - timedelta(days=CACHE_DAYS)).order_by('-query').first()
    if cached:
        ExternalPartSearch.objects.filter(pk=cached.pk).update(search_count=cached.search_count + 1)
        return cached.results, cached.query[7:], True

    digikey = get_digikey()
    if not digikey.is_configured or cache.get('digikey_remaining', 1000) <= DIGIKEY_RESERVE:
        raise SearchUnavailable('DigiKey search budget for today is used up')
    try:
        for stem in stems[:FAMILY_MAX_CALLS]:
            hits = [h for h in digikey_keyword(digikey, stem, limit=KEYWORD_LIMIT)
                    if str(h.get('mpn', '')).upper().startswith(stem)]
            if hits:
                break
        else:
            return [], stems[0], False
    except Exception as exc:
        logger.warning('DigiKey family search failed for %s: %s', part_number, exc)
        raise SearchUnavailable(f'DigiKey did not answer ({exc})')
    finally:
        if digikey.remaining is not None:
            cache.set('digikey_remaining', digikey.remaining, 6 * 3600)
    kept = {}
    for hit in hits:
        status = str(hit.get('status') or '')
        fit = {'score': (2 if status.lower() == 'active' else -2 if status.lower().startswith('obsolete') else 0)
               + (1 if (hit.get('stock') or 0) > 0 else 0),
               'notes': [status] if status and status.lower() != 'active' else [], 'value': 'family'}
        row = {**{k: v for k, v in hit.items() if k != 'source'}, 'sources': [hit.get('source', 'digikey')], 'fit': fit}
        # packaging variants share a description: one line each, but an Active part and its
        # not-for-new-designs sibling are both worth seeing
        key = (row.get('manufacturer', ''), re.sub(r'\s+', ' ', (row.get('description') or '').strip().lower()), status.lower())
        if key not in kept or (row.get('stock') or 0) > (kept[key].get('stock') or 0):
            kept[key] = row
    results = sorted(kept.values(), key=lambda h: (-h['fit']['score'], -(h.get('stock') or 0)))[:MAX_RESULTS]
    ExternalPartSearch.objects.update_or_create(
        query=f'FAMILY {stem}', defaults={'results': results, 'sources': ['digikey', 'family'],
                                          'fetched_at': timezone.now(), 'search_count': 1})
    return results, stem, False
