"""
Schematic value labels -> component fields.

A laptop schematic prints, beside each part's reference designator, a label the board's
designer (the ODM) writes in its own house format:

    Compal / LCFC   0.1U_0402_16V7K    10K_0402_5%    BLM18PG471SN1D_2P    330U_D2_2VM_R9M
    Apple, Samsung  1UF  10%  6.3V  X5R  0201      (each field on its own line)

parse_label() reads the words gathered around one designator and returns what they say:
the kind of part, its ratings, package, and a maker part number when one is printed. Only
formats checked against real data are decoded:

  * Compal's capacitor code '16V7K' (voltage, dielectric digit, tolerance letter) was
    checked by joining five Compal schematics with their factory BOMs on the designator
    (~4,500 parts): 6 = X5R (853 of 874), 7 = X7R (323/327), 8 = C0G (78/86),
    A = X6S (265/270), 4 = Y5V.
  * Fields written with their unit ('1UF', '6.3V', '10%', 'X5R', '0402') are read as such.
  * Maker part numbers go through the component decoders (spec_parse.decode_mpn).

Other ODMs' size digits ('2.2U/6.3V_4', '0.1u/2/X5R/16V/K') are not guessed: the label's
explicit fields are still read, the size is left for a person.
"""
import re
from fractions import Fraction

from apps.components.spec_parse import (
    SITE_TYPE, VALUE_KEYS, conflicts, decode_mpn, guess_maker, parse_description,
)

# what a designator's letters say the part is
DESIGNATOR_KIND = [(r'^(?:FB|FL|BL)\d', 'ferrite'), (r'^(?:R|RV|PR|RP|RA|RN|VR)\d', 'resistor'),
                   (r'^(?:C|CV|PC|CP|EC|BC)\d', 'capacitor'), (r'^(?:L|LV|PL)\d', 'inductor'),
                   (r'^(?:RT|TH|NTC)\d', 'thermistor'), (r'^(?:Y|X|OSC)\d', 'crystal'), (r'^(?:F|PF)\d', 'fuse')]
IMPERIAL = ('01005', '0201', '0402', '0603', '0805', '1008', '1206', '1210', '1806', '1812', '2010', '2512')

# Compal / LCFC: dielectric digit in the capacitor code
COMPAL_DIEL = {'4': 'Y5V', '6': 'X5R', '7': 'X7R', '8': 'C0G', 'A': 'X6S'}
TOL_LETTER = {'B': '±0.1pF', 'C': '±0.25pF', 'D': '±0.5pF', 'F': '1%', 'G': '2%', 'J': '5%', 'K': '10%',
              'M': '20%', 'Z': '+80/-20%'}
UNIT_PF = {'P': 1, 'N': 1e3, 'U': 1e6}
NUM = r'(\d*\.?\d+)'
# 0.1U_0402_16V7K, 22U_0603_6.3V6-M, 0.1U_25V_K_X7R_0402 (LCFC)
COMPAL_CAP = re.compile(rf'^{NUM}([PNU])F?_(\d{{4}})_{NUM}V([4678A])-?([BCDFGJKMZ])?$', re.I)
LCFC_CAP = re.compile(rf'^{NUM}([PNU])F?_{NUM}V_([BCDFGJKMZ])_(X5R|X7R|X6S|X7S|C0G|NPO|NP0|Y5V)_(\d{{4}})$', re.I)
# 4.7K_0402_5%, 24.9_0402_1%, 0_0805_5%, 0.01_1206_1%
COMPAL_RES = re.compile(rf'^{NUM}([KMR]?)_(\d{{4}})_{NUM}%$', re.I)
# 330U_D2_2VM_R9M, 220U_D2_6.3VY_R15M: polymer capacitor, case, voltage, tolerance, ESR
COMPAL_POLY = re.compile(rf'^{NUM}U_([A-Z]\d?)_{NUM}V([MYK])?(?:_R{NUM}M)?$', re.I)
# 2.2UH_LQM2MPN2R2NG0L_30%, 4.7UH_PCMB063T-4R7MS_5.5A_20%
COMPAL_IND = re.compile(rf'^{NUM}([UN])H_([A-Z0-9][A-Z0-9-]+)(?:_{NUM}A)?(?:_{NUM}%)?$', re.I)
# 100K_0402_1%_NCP15WF104F03RC, 100K_0402_1%_B25/50
COMPAL_THERM = re.compile(rf'^{NUM}([KM]?)B?_(\d{{4}})_{NUM}%_(\S+)$', re.I)
# a maker part number followed by its pin count or size: BLM18PG471SN1D_2P, HCB2012KF-121T50_0805
PN_TAIL = re.compile(r'^([A-Z][A-Z0-9-]{5,})_(\d{4}|\dP)$', re.I)

# '*0_04' (Quanta, Clevo) and a lone '@' (Compal): not fitted by default; 'PX@', 'DIS@0.1U/10V_4X': fitted
# only in that build
NOT_FITTED = re.compile(r'^\*|^@$')
VARIANT = re.compile(r'^([A-Z0-9]+)@', re.I)
IC_PN = re.compile(r'^(?=.*\d)(?=.*[A-Z])[A-Z0-9][A-Z0-9-]{5,}$')
SAME_KIND = {('inductor', 'ferrite'), ('ferrite', 'inductor'), ('resistor', 'thermistor')}


def designator_kind(designator):
    return next((k for pattern, k in DESIGNATOR_KIND if re.match(pattern, designator or '', re.I)), None)


def _ohms(num, mult):
    return round(float(num) * {'': 1, 'R': 1, 'K': 1e3, 'M': 1e6}[mult.upper()], 6)


def _clean(token):
    """(token without stuffing/variant marks and Compal's '~D' tail, flags)."""
    flags = []
    t = token.strip()
    if t.endswith('~D'):
        t = t[:-2]
    if NOT_FITTED.search(t):
        flags.append('not fitted by default')
        t = t.strip('*@')
    m = VARIANT.match(t)
    if m:
        flags.append(f'fitted in build {m.group(1).upper()} only')
        t = t[m.end():]
    return t, flags


def parse_token(token, kind=None):
    """One label word -> (kind, specs, package, (maker, part number) or None), or None."""
    t, _ = _clean(token)
    m = COMPAL_CAP.match(t)
    if m:
        spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6),
                'voltage_v': float(m.group(4)), 'dielectric': COMPAL_DIEL[m.group(5).upper()]}
        if m.group(6):                                  # '0.1U_0402_25V6': the letter left off
            spec['tolerance'] = TOL_LETTER[m.group(6).upper()]
        return 'capacitor', spec, m.group(3), None
    m = LCFC_CAP.match(t)
    if m:
        diel = {'NPO': 'C0G', 'NP0': 'C0G'}.get(m.group(5).upper(), m.group(5).upper())
        return 'capacitor', {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6),
                             'voltage_v': float(m.group(3)), 'tolerance': TOL_LETTER[m.group(4).upper()],
                             'dielectric': diel}, m.group(6), None
    m = COMPAL_THERM.match(t)
    if m and kind in (None, 'thermistor'):
        rest = m.group(5)
        pn = rest if re.search(r'[A-Z]{2,}\d', rest, re.I) and '/' not in rest else None
        return 'thermistor', {'resistance_ohm': _ohms(m.group(1), m.group(2)), 'tolerance': f'{float(m.group(4)):g}%'}, \
            m.group(3), (None, pn) if pn else None
    m = COMPAL_RES.match(t)
    if m:
        k = 'thermistor' if kind == 'thermistor' else 'resistor'
        return k, {'resistance_ohm': _ohms(m.group(1), m.group(2)), 'tolerance': f'{float(m.group(4)):g}%'}, \
            m.group(3), None
    m = COMPAL_POLY.match(t)
    if m:
        spec = {'capacitance_pf': round(float(m.group(1)) * 1e6, 3), 'voltage_v': float(m.group(3)),
                'dielectric': 'polymer'}
        if m.group(4) and m.group(4).upper() in 'MK':
            spec['tolerance'] = TOL_LETTER[m.group(4).upper()]
        return 'capacitor', spec, None, None
    m = COMPAL_IND.match(t)
    if m:
        spec = {'inductance_uh': round(float(m.group(1)) * (1 if m.group(2).upper() == 'U' else 1e-3), 6)}
        if m.group(4):
            spec['current_a'] = float(m.group(4))
        if m.group(5):
            spec['tolerance'] = f'{float(m.group(5)):g}%'
        return 'inductor', spec, None, (None, m.group(3))
    m = PN_TAIL.match(t)
    pn = m.group(1) if m else t
    maker = guess_maker(pn.upper())
    if maker and len(pn) >= 6:
        d = decode_mpn(maker, pn.upper())
        if d:
            size = m.group(2) if m and m.group(2) in IMPERIAL else None
            return SITE_TYPE.get(d[0], d[0]), d[1], d[2] or size, (maker, pn)
    return None


def _explicit(tokens, kind):
    """Fields written with their unit across the label's words: '1UF 10% 6.3V X5R 0201'."""
    words = [t for t in (_clean(w)[0] for w in tokens) if t]
    if not words:
        return None
    parts = re.sub(r'[_/,]', ' ', ' '.join(words)).split()   # '0.1U/10V_4X', '0.22uF/16V,X7R'
    # after the value, a bare one- or two-digit word is an ODM's size code ('34_4', '*0_04'), not a value
    text = ' '.join(parts[:1] + [w for w in parts[1:] if not re.fullmatch(r'\d{1,2}', w)])
    k, specs, pkg = parse_description(text, kind or '')
    specs = dict(specs)
    first = text.split()[0] if text.split() else ''
    if kind in ('resistor', 'thermistor') and 'resistance_ohm' not in specs:
        m = re.fullmatch(r'(\d*\.?\d+)([KMR]?)(\d*)', first, re.I)        # '34', '10K', '4K7', '1M'
        if m and not (m.group(3) and not m.group(2)):
            v = float(m.group(1) + ('.' + m.group(3) if m.group(3) else ''))
            specs['resistance_ohm'] = round(v * {'': 1, 'R': 1, 'K': 1e3, 'M': 1e6}[m.group(2).upper()], 6)
        letter = next((w for w in text.split()[1:] if re.fullmatch(r'[FGJ]', w, re.I)), None)
        if letter and 'tolerance' not in specs:
            specs['tolerance'] = TOL_LETTER[letter.upper()]           # EIA letter: '1K/F_4' is 1%
    if not specs and not pkg:
        return None
    return SITE_TYPE.get(k, k) if k else kind, specs, pkg, None


def parse_label(tokens, designator):
    """Words gathered around one designator -> {'kind', 'specs', 'package', 'maker', 'part_number',
    'flags', 'confidence', 'used'}. confidence: 'high' when a known label format gives the value and the
    designator agrees on the kind, 'medium' when only some fields could be read, 'low' when none."""
    want = designator_kind(designator)
    flags = sorted({f for t in tokens for f in _clean(t)[1]})
    found, used, other = [], [], []
    for t in tokens:
        r = parse_token(t, want)
        if r and (want is None or r[0] in (want, None) or (want, r[0]) in SAME_KIND):
            found.append(r)
            used.append(t)
        elif r:
            other.append(t)                 # another part's label ('0_0402_5%' beside a capacitor)
    rest = [t for t in tokens if t not in used and t not in other]
    explicit = _explicit(rest, want) if rest else None
    if explicit and (want is None or explicit[0] in (want, None)):
        found.append(explicit)
    out = {'kind': want, 'specs': {}, 'package': None, 'maker': None, 'part_number': None,
           'flags': flags, 'confidence': 'low', 'used': used}
    clash = False
    for kind, specs, pkg, pn in found:
        if kind and (out['kind'], kind) in SAME_KIND and pn:
            out['kind'] = kind                  # an L designator on a bead: the part number says ferrite
        out['kind'] = out['kind'] or kind
        bad = conflicts(out['specs'], specs)
        if any(k in VALUE_KEYS for k in bad):
            clash = True
            continue
        out['specs'].update({k: v for k, v in specs.items() if k not in bad})
        out['package'] = out['package'] or pkg
        if pn and not out['part_number']:
            out['maker'], out['part_number'] = pn
    if not found and want not in ('resistor', 'capacitor', 'inductor', 'ferrite', 'thermistor'):
        # a chip's label is its part number; the maker is left for the reviewer
        pn = next((c for c in (_clean(t)[0] for t in tokens) if IC_PN.match(c.upper())), None)
        if pn:
            out['part_number'] = pn
            out['confidence'] = 'medium'
            return out
    has_value = any(k in out['specs'] for k in VALUE_KEYS) or bool(out['part_number'])
    fields = len(out['specs']) + bool(out['package'])
    agrees = out['kind'] == want or (want, out['kind']) in SAME_KIND or want is None
    if has_value and not clash and agrees and (used or fields >= 3):
        out['confidence'] = 'high'
    elif has_value or out['package']:
        out['confidence'] = 'medium'
    if clash:
        out['flags'].append('the label names two different values')
    return out


def _fmt_ohm(v):
    if v >= 1e6:
        return f'{v / 1e6:g}M'
    if v >= 1e3:
        return f'{v / 1e3:g}K'
    return f'{v:g}R'


def _fmt_farad(pf):
    if pf >= 1e6:
        return f'{pf / 1e6:g}uF'
    if pf >= 1e3:
        return f'{pf / 1e3:g}nF'
    return f'{pf:g}pF'


def generic_name(kind, specs, package):
    """The Generic part's number, in the site's style ('CAP 100nF 16V X7R 10% 0402',
    'RES 4.7K 5% 0402'), from the fields known; None without a value."""
    s, pkg = specs, package or ''
    if kind == 'resistor' and 'resistance_ohm' in s:
        if s['resistance_ohm'] == 0:
            return f'RES 0R JUMPER {pkg}'.strip()
        power = f"{Fraction(s['power_w']).limit_denominator(100)}W" if s.get('power_w') else ''
        return ' '.join(x for x in ('RES', _fmt_ohm(s['resistance_ohm']), s.get('tolerance', ''), power, pkg) if x)
    if kind == 'capacitor' and 'capacitance_pf' in s:
        volt = f"{s['voltage_v']:g}V" if s.get('voltage_v') else ''
        return ' '.join(x for x in ('CAP', _fmt_farad(s['capacitance_pf']), volt, s.get('dielectric', ''),
                                    s.get('tolerance', ''), pkg) if x)
    if kind == 'inductor' and 'inductance_uh' in s:
        cur = f"{s['current_a']:g}A" if s.get('current_a') else ''
        return ' '.join(x for x in ('IND', f"{s['inductance_uh']:g}uH", s.get('tolerance', ''), cur, pkg) if x)
    if kind == 'ferrite' and 'impedance_ohm' in s:
        return ' '.join(x for x in ('FERRITE', f"{s['impedance_ohm']:g}R@100MHz", pkg) if x)
    if kind == 'thermistor' and 'resistance_ohm' in s:
        return ' '.join(x for x in ('NTC', _fmt_ohm(s['resistance_ohm']), s.get('tolerance', ''), pkg) if x)
    return None
