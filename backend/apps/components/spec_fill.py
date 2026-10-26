"""
Apply apps.components.spec_parse to Component rows: fill the ratings a component
is missing from its description and part number. Stored values are not
overwritten - a disagreement is returned for a person to look at instead - except,
when the caller says the stored ratings were written by an importer, a rating the
part number itself decides (trust_part_number).
"""
from .spec_parse import SITE_TYPE, VALUE_KEYS, conflicts, decode_mpn, derive

# one quantity, several possible storage keys: a component that has any of them has the value
SAME_QUANTITY = [
    {'capacitance_pf', 'capacitance_nf', 'capacitance_uf'},
    {'inductance_uh', 'inductance_nh'},
    {'tolerance', 'tolerance_pct'},
]
UNITS = {'capacitance_nf': ('capacitance_pf', 1e3), 'capacitance_uf': ('capacitance_pf', 1e6),
         'inductance_nh': ('inductance_uh', 1e-3)}


def normalise_legacy(specs, parsed=None):
    """'tolerance_pct': 5 -> 'tolerance': '5%' (the key every importer and the filters use).
    An earlier lookup import stored '-20/+80%' as 80; the parsed text, when it has a
    tolerance, is the better source. Returns the keys changed."""
    changed = []
    if 'tolerance_pct' in specs and 'tolerance' not in specs:
        pct = specs.pop('tolerance_pct')
        specs['tolerance'] = (parsed or {}).get('tolerance') or f'{float(pct):g}%'
        changed.append('tolerance')
    return changed


def _comparable(stored):
    """Stored specs in the parser's units, for comparing."""
    out = dict(stored)
    for key, (base, mult) in UNITS.items():
        if key in out and base not in out and isinstance(out[key], (int, float)):
            out[base] = round(out[key] * mult, 9)
    return out


def _has(specs, key):
    for group in SAME_QUANTITY:
        if key in group:
            return bool(group & set(specs))
    return key in specs


def plan(component, text=None, trust_part_number=False):
    """What filling would change, without saving: {'specs', 'package', 'type', 'derived',
    'added', 'corrected', 'conflict'}. `text` overrides the description as the source (a part's
    own BOM line). trust_part_number: the stored ratings were written by an importer, not a
    person, so a rating the part number decides replaces a stored one that contradicts it."""
    derived = derive(component.manufacturer, component.part_number,
                     component.description if text is None else text, component.component_type)
    specs = dict(component.specifications or {})
    added = normalise_legacy(specs, derived['specs'])
    clash = [k for k in conflicts(_comparable(specs), derived['specs']) if k != 'tolerance' or 'tolerance' not in added]
    corrected = []
    decoded = decode_mpn(component.manufacturer, component.part_number)
    if trust_part_number and decoded:
        for key in list(clash):
            if key in decoded[1] and key in specs:
                specs[key] = decoded[1][key]
                corrected.append(key)
                clash.remove(key)
    for key, value in derived['specs'].items():
        if not _has(specs, key) and key not in clash:
            specs[key] = value
            added.append(key)
    package = component.package_type or (derived['package'] or '')[:50]
    if component.package_type and derived['package'] and component.package_type != derived['package'] \
            and derived['source'] and 'part number' in derived['source']:
        clash.append('package')
    kind_type = SITE_TYPE.get(derived['kind']) if derived['kind'] else None
    return {'specs': specs, 'package': package, 'type': kind_type, 'derived': derived, 'added': added,
            'corrected': corrected, 'conflict': sorted(set(clash)),
            'overridden': [k for k in derived['conflict'] if k not in VALUE_KEYS],
            'disputed': [k for k in derived['conflict'] if k in VALUE_KEYS]}


def fill(component, text=None, save=True):
    """Fill missing ratings and package in place. Returns the plan()."""
    p = plan(component, text)
    fields = []
    if p['added'] or p['corrected']:
        component.specifications = p['specs']
        fields.append('specifications')
    if p['package'] != component.package_type:
        component.package_type = p['package']
        fields.append('package_type')
    if save and fields:
        component.save(update_fields=fields)
    p['fields'] = fields
    return p
