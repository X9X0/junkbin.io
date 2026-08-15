"""
Parsers that recover a component's primary value from the freeform BOM text
scanned/OCR'd out of service manuals (Component.specifications is often
empty for bulk-imported BOMs even though the raw manual text is right there
in ProductComponent.notes, e.g. "5% CERAMIC CHIP 470PF | 50V").

Each parser looks only at the text before the first "|" - anything after
that is voltage/tolerance/OCR bleed from an adjacent table row and is not
part of this component's value. A parser returns None rather than guessing
when nothing in the text cleanly matches, so callers only get high-confidence
values.

Values are normalized to the unit that Component.primary_value's formatters
expect (resistance in ohms, capacitance in nanofarads, inductance in
microhenries) so the whole magnitude range renders through a single
formatter without extra unit-key bookkeeping.
"""
import re

# Scanned service manuals run through OCR, which reliably confuses these
# letter/digit pairs (the previous manual BOM cleanup hand-corrected one
# instance of this, "63K" -> "68K"). Only applied to tokens that are
# otherwise entirely digits/confusable letters plus a known unit suffix, so
# real words never reach this substitution.
_OCR_DIGIT_FIXES = str.maketrans({
    'O': '0', 'o': '0',
    'I': '1', 'i': '1', 'L': '1', 'l': '1', '!': '1',
    'S': '5', 's': '5',
    'B': '8', 'b': '8',
    'J': '1', 'j': '1',
})
_DIGIT_CHARS = '0-9OoIiLlSsBbJj!'


_SPLIT_PERCENT = re.compile(r'(?<!\S)%\s+(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s+%(?!\S)')
_SPLIT_KM_SUFFIX = re.compile(r'(\d+(?:\.\d+)?)\s+([KM])(?!\S)', re.IGNORECASE)


def _head(notes):
    """Text before the first '|' - where the value token actually lives.

    OCR sometimes splits a tolerance like "1%" across whitespace into
    separate "%" and "1" tokens (e.g. "% 1 CARBON 470"), or splits a
    resistor's K/M multiplier off into its own token (e.g. "GLAZE 1 K 5%").
    Re-glue both before tokenizing so a bare digit isn't mistaken for the
    component's value."""
    head = notes.split('|', 1)[0]
    head = _SPLIT_PERCENT.sub(lambda m: (m.group(1) or m.group(2)) + '%', head)
    return _SPLIT_KM_SUFFIX.sub(lambda m: m.group(1) + m.group(2).upper(), head)


def _repaired_tokens(notes, suffixes):
    """Yield every original whitespace-separated token from the head (in
    order), then - only for tokens that are entirely digits/confusable
    letters plus one of `suffixes` - the OCR-digit-repaired copy of that
    token (also in order). Clean matches anywhere in the string are tried
    before any repaired guess, so a garbled early token never pre-empts a
    legitimate later one."""
    suffix_pattern = '|'.join(suffixes)
    garbled = re.compile(rf'^([{_DIGIT_CHARS}.]+)({suffix_pattern})$', re.IGNORECASE)
    tokens = _head(notes).replace(',', ' ').split()
    yield from tokens
    for token in tokens:
        m = garbled.match(token)
        if m:
            digits, unit = m.groups()
            yield digits.translate(_OCR_DIGIT_FIXES) + unit.upper()


def parse_resistor_ohms(notes):
    """Return resistance in ohms from the first bare/K/M value token, or None."""
    multiplier = {'': 1, 'K': 1_000, 'M': 1_000_000}
    pattern = re.compile(r'^(\d+(?:\.\d+)?)([KM]?)$', re.IGNORECASE)
    for token in _repaired_tokens(notes, ('', 'K', 'M')):
        if token.endswith('%'):
            continue
        m = pattern.match(token)
        if m:
            value, suffix = m.groups()
            return float(value) * multiplier[suffix.upper()]
    return None


def parse_capacitor_nf(notes):
    """Return capacitance in nanofarads from the first PF/MF value token, or None."""
    pattern = re.compile(r'^(\d+(?:\.\d+)?)(PF|MF)$', re.IGNORECASE)
    for token in _repaired_tokens(notes, ('PF', 'MF')):
        m = pattern.match(token)
        if m:
            value, unit = m.groups()
            value = float(value)
            return value / 1_000 if unit.upper() == 'PF' else value * 1_000
    return None


def parse_inductor_uh(notes):
    """Return inductance in microhenries from the first UH/MH value token, or None."""
    pattern = re.compile(r'^(\d+(?:\.\d+)?)(UH|MH)$', re.IGNORECASE)
    for token in _repaired_tokens(notes, ('UH', 'MH')):
        m = pattern.match(token)
        if m:
            value, unit = m.groups()
            value = float(value)
            return value * 1_000 if unit.upper() == 'MH' else value
    return None


PARSERS = {
    'resistor': ('resistance_ohm', parse_resistor_ohms),
    'capacitor': ('capacitance_nf', parse_capacitor_nf),
    'inductor': ('inductance_uh', parse_inductor_uh),
}


# Construction-type keywords, longest/most-specific match first so e.g.
# "METAL CHIP" wins over the plain "METAL" fallback. Includes the specific
# OCR-garbled spellings actually observed in this manual's BOM text (see
# apps.components.management.commands.backfill_component_values) rather than
# a general letter-repair pass - description text is user-visible, so an
# unmatched construction word is left out rather than guessed at.
_CONSTRUCTION_KEYWORDS = {
    'resistor': [
        ('METAL GLAZE', 'Metal glaze'), ('METALGLAZE', 'Metal glaze'), ('MET AL GLAZE', 'Metal glaze'),
        ('METAL CHIP', 'Metal film chip'), ('METALCHIP', 'Metal film chip'), ('MET AL CHIP', 'Metal film chip'),
        ('METAL OXIDE', 'Metal oxide'),
        ('METAL FILM', 'Metal film'),
        ('ME1A1', 'Metal film'), ('METAL', 'Metal film'),
        ('CAR80N', 'Carbon film'), ('CARBON', 'Carbon film'),
        ('WIREWOUND', 'Wirewound'),
        ('FUSIBLE', 'Fusible'),
    ],
    'capacitor': [
        ('CERAMICCHIP', 'Ceramic chip'), ('CERAMIC CHIP', 'Ceramic chip'), ('CERAMIC', 'Ceramic'),
        ('ELECT', 'Electrolytic'),
        ('TANTALUM', 'Tantalum'),
        ('MYLAR', 'Mylar film'),
        ('FILM', 'Film'),
    ],
    'inductor': [
        ('FERRITE BEAD', 'Ferrite bead'),
        ('INDUCTOR CHIP', 'Chip'),
        ('COIL', 'Coil'),
        # Bare "INDUCTOR" with no more specific construction word is left
        # unmatched (falls through to None) - it's already redundant with
        # the component-type badge shown alongside the description.
    ],
}
_TYPE_NOUN = {'resistor': 'resistor', 'capacitor': 'capacitor', 'inductor': 'inductor'}

_TOLERANCE_TOKEN = re.compile(r'(\d+(?:\.\d+)?)\s*%')
_VOLTAGE_TOKEN = re.compile(r'\b(\d+(?:\.\d+)?)\s*(K?V)\b', re.IGNORECASE)
_WATTAGE_TOKEN = re.compile(r'\b(\d+/\d+|\d+(?:\.\d+)?)\s*W\b', re.IGNORECASE)


def parse_description(component_type, notes):
    """Build a short human-readable description from construction type,
    tolerance, and voltage/wattage rating, or None if the construction type
    isn't recognized. Rating (voltage/wattage) is read from after the first
    '|' - that's where this manual puts it - while tolerance is read from
    before it, alongside the value."""
    keywords = _CONSTRUCTION_KEYWORDS.get(component_type)
    if not keywords:
        return None

    head_upper = _head(notes).upper()
    construction = next((label for needle, label in keywords if needle in head_upper), None)
    if construction is None:
        return None

    noun = _TYPE_NOUN[component_type]
    headline = construction if noun in construction.lower() else f'{construction} {noun}'
    parts = [headline]

    tolerance = _TOLERANCE_TOKEN.search(_head(notes))
    if tolerance:
        parts.append(f'±{tolerance.group(1)}% tolerance')

    rating_text = notes.split('|', 1)[1] if '|' in notes else ''
    wattage = _WATTAGE_TOKEN.search(rating_text)
    if wattage:
        parts.append(f'{wattage.group(1)}W')
    else:
        voltage = _VOLTAGE_TOKEN.search(rating_text)
        if voltage:
            unit = 'kV' if voltage.group(2).upper() == 'KV' else 'V'
            parts.append(f'{voltage.group(1)}{unit} rating')

    return ', '.join(parts)
