"""
Parses a human-typed component value query (e.g. "10k", "4.7uF", "100nF",
"16MHz", "3.3V", "500mA") and resolves it against Component.specifications
so a search for "10k" finds every resistor whose specifications.resistance_ohm
is ~10000 - a real numeric match against the same JSON keys
Component.primary_value reads from - rather than a substring match against
free text that happens to contain "10k".

Two-step process:
  1. parse_value_query() reads the query into (kind, magnitude), where kind
     is a physical quantity (resistance/capacitance/inductance/frequency/
     voltage/current) and magnitude is in that quantity's base SI unit
     (ohms/farads/henries/hertz/volts/amps). Returns None if the text isn't
     a value at all (not a search bug - callers should treat that as "no
     matches" rather than silently ignoring the filter).
  2. spec_key_candidates() converts that magnitude into every
     specifications key that quantity could be stored under (components
     store capacitance under whichever of _nf/_pf/_uf was convenient at
     entry time, for example) so the filter can OR across all of them.

Unit letters are unambiguous ("16MHz" is always frequency). A bare number
with only an SI prefix and no unit letter ("10k", "4.7u", "220p") is
resolved by the convention each prefix is overwhelmingly used for in
practice - this is the same "no unit = resistor shorthand" convention
apps.components.value_parsing.parse_resistor_ohms already relies on for
bare-number resistor values.
"""
import re

# (base-unit-magnitude, stored-unit-magnitude) converters, one per
# specifications key that Component.primary_value's extraction_rules read
# a given physical quantity from.
_KIND_SPEC_KEYS = {
    'resistance': [
        ('resistance_ohm', lambda ohms: ohms),
    ],
    'capacitance': [
        ('capacitance_nf', lambda farads: farads * 1e9),
        ('capacitance_pf', lambda farads: farads * 1e12),
        ('capacitance_uf', lambda farads: farads * 1e6),
    ],
    'inductance': [
        ('inductance_uh', lambda henries: henries * 1e6),
        ('inductance_nh', lambda henries: henries * 1e9),
    ],
    'frequency': [
        ('frequency_mhz', lambda hz: hz / 1e6),
        ('frequency_ghz', lambda hz: hz / 1e9),
        ('frequency_khz', lambda hz: hz / 1e3),
    ],
    'voltage': [
        ('voltage_v', lambda v: v),
        ('vf_v', lambda v: v),
        ('vds_v', lambda v: v),
        ('vce_v', lambda v: v),
    ],
    'current': [
        ('current_a', lambda a: a),
        ('iout_a', lambda a: a),
        ('output_a', lambda a: a),
        ('charge_current_a', lambda a: a),
    ],
}

# Prefix characters immediately following the number. Case matters only for
# 'm' vs 'M' (milli vs mega) - every other prefix letter is safe to fold.
_PREFIX_MULTIPLIER = {
    'p': 1e-12, 'P': 1e-12,
    'n': 1e-9, 'N': 1e-9,
    'u': 1e-6, 'U': 1e-6, 'µ': 1e-6,
    'm': 1e-3,
    'k': 1e3, 'K': 1e3,
    'M': 1e6,
    'g': 1e9, 'G': 1e9,
}

# Explicit unit letters are unambiguous.
_UNIT_KIND = {
    'ohm': 'resistance', 'ohms': 'resistance', 'ω': 'resistance', 'r': 'resistance',
    'f': 'capacitance',
    'h': 'inductance',
    'hz': 'frequency',
    'v': 'voltage',
    'a': 'current',
}

# No unit letter given - resolve from the prefix alone, per the convention
# that prefix is overwhelmingly used for among hobbyist-typed component
# values (a bare "10k" is a 10k resistor, not 10 kHz; a bare "220p" is
# 220pF, essentially never 220 picohenries).
_BARE_PREFIX_KIND = {
    '': 'resistance',
    'k': 'resistance', 'K': 'resistance',
    'M': 'resistance',
    'p': 'capacitance', 'P': 'capacitance',
    'n': 'capacitance', 'N': 'capacitance',
    'u': 'capacitance', 'U': 'capacitance', 'µ': 'capacitance',
    'm': 'inductance',
    'g': 'frequency', 'G': 'frequency',
}

_VALUE_RE = re.compile(r'^\s*([+-]?\d+(?:\.\d+)?)\s*([a-zA-ZΩµ]*)\s*$')

# Real component values follow spaced-out standard series (E12/E24/...) -
# 5% comfortably absorbs float/storage noise without bleeding into a
# neighboring standard value.
TOLERANCE = 0.05


def parse_value_query(text):
    """Parse a value query into (kind, magnitude_in_base_si_unit), or None
    if the text can't be read as a component value at all."""
    if not text:
        return None
    m = _VALUE_RE.match(text)
    if not m:
        return None

    number_str, rest = m.groups()
    number = float(number_str)

    prefix, unit = '', rest
    if rest and rest[0] in _PREFIX_MULTIPLIER:
        prefix, unit = rest[0], rest[1:]

    magnitude = number * _PREFIX_MULTIPLIER.get(prefix, 1.0)

    if unit:
        kind = _UNIT_KIND.get(unit.lower())
    else:
        kind = _BARE_PREFIX_KIND.get(prefix)

    if kind is None:
        return None
    return kind, magnitude


def spec_key_candidates(kind, magnitude):
    """(specifications_key, low, high) tuples to OR together for this kind/
    magnitude - one per key that quantity might be stored under."""
    candidates = []
    for key, to_stored_unit in _KIND_SPEC_KEYS.get(kind, []):
        target = to_stored_unit(magnitude)
        lo, hi = target * (1 - TOLERANCE), target * (1 + TOLERANCE)
        if lo > hi:
            lo, hi = hi, lo
        candidates.append((key, lo, hi))
    return candidates
