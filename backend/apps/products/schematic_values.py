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

  * Quanta, Clevo, Inventec and Wistron size codes were read off their own boardviews (GenCAD
    files list each part's footprint and its schematic value): Quanta _2/_4/_6/_8/_12 = 0201/0402/
    0603/0805/1206, Clevo _04/_06/_08, Inventec _1/_2/_3/_6 (its _5 sits on three sizes: not read),
    Wistron's size digit 2/3/5 = 0402/0603/0805. The same digit means different sizes to different
    ODMs (Quanta _2 = 0201, Inventec _2 = 0402), so these are read only when detect_odm() has named
    the document's ODM from its title blocks or board numbers.

Gigabyte's and MSI's size digits ('0.1u/2/X5R/16V/K') are not guessed: the label's explicit
fields are still read, the size is left for a person.
"""
import re
from fractions import Fraction

from apps.components.spec_parse import (
    SITE_TYPE, VALUE_KEYS, conflicts, decode_mpn, guess_maker, parse_description,
)

# what a designator's letters say the part is
DESIGNATOR_KIND = [(r'^(?:FB|FL|BL)\d', 'ferrite'), (r'^(?:R|RV|PR|RP|RA|RN|VR)\d', 'resistor'),
                   (r'^(?:C|CV|PC|CP|EC|BC)\d', 'capacitor'), (r'^(?:L|LV|PL)\d', 'inductor'),
                   (r'^(?:RT|TH|NTC)\d', 'thermistor'), (r'^(?:Y|X|OSC)\d', 'crystal'), (r'^(?:F|PF)\d', 'fuse'),
                   # chips: a passive's house code must not be read off a Q, D or U label ('2N7002_NC' on an
                   # MSI board is a MOSFET, not a 2 nF 700 V 0402 capacitor)
                   (r'^(?:Q|PQ|MQ|TR)\d', 'transistor'), (r'^(?:D|PD|ZD|CR)\d', 'diode'), (r'^(?:U|PU|IC)\d', 'ic')]
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
# who drew a schematic: words its title blocks and board numbers carry
ODM_MARKS = [('compal', r'Compal Electronics|\bLA-[0-9A-Z]{4}P\b'), ('lcfc', r'\bLCFC\b|\bNM-[A-Z]\d{3}\b'),
             ('quanta', r'Quanta Computer|\bDA0[0-9A-Z]{3}MB|\bDAZ[0-9A-Z]{5}'), ('inventec', r'Inventec|\b6050A\d{7}'),
             ('wistron', r'Wistron'), ('clevo', r'\bCLEVO\b|\b6-7[17]-[0-9A-Z]{5}'),
             ('msi', r'MICRO-STAR|\bMS-\d{4}\b'),
             # Tongfang title blocks carry no maker name: its capacitor labels are the mark ('.1U-10-04R-K')
             ('tongfang', r'(?<![\w.])@?\d*\.?\d+[PNU]F?-\d*\.?\d+-\d\d[RXNY]-[BCDFGJKMZ]\b'),
             # Gigabyte boards: the title block ('GIGA-BYTE TECHNOLOGY') or the capacitor labels,
             # value/size/dielectric/volts/tolerance ('0.01U/4/X7R/16V/K')
             ('gigabyte', r'GIGA-?BYTE|(?<![\w.])\d*\.?\d+[PNU]/\d{1,2}/(?:X5R|X7R|NPO|Y5V|X6S)/\d*\.?\d+V/[BCDFGJKMZX]\b')]
ODM_SIZE = {'quanta': {'2': '0201', '4': '0402', '6': '0603', '8': '0805', '12': '1206'},
            'clevo': {'02': '0201', '04': '0402', '06': '0603', '08': '0805'},
            'inventec': {'1': '0201', '2': '0402', '3': '0603', '6': '1206'},
            'wistron': {'1': '0201', '2': '0402', '3': '0603', '5': '0805'},
            'msi': {'2': '0402', '4': '0402', '6': '0603', '8': '0805', '12': '1206', '04': '0402', '06': '0603',
                    '08': '0805'},
            'tongfang': {'02': '0201', '04': '0402', '06': '0603', '08': '0805', '12': '1206'},
            'gigabyte': {'4': '0402', '6': '0603', '8': '0805', '12': '1206'}}
# Gigabyte: 0.1U/6/Y5V/25V/Z, 33P/4/NPO/50V/J, 22/4, 20K/4/1 (1%); size digit read off 2 boardviews (1,926
# parts: /4 0402 in 1,310 of 1,311, /6 0603, /8 0805, /12 1206). A trailing 'X' is left unread.
# Server boards abbreviate the dielectric to one letter ('0.01U/6/X/50V/B', '22P/4/N/50V/X'): the size and
# voltage are read, the letter is not (unverified against a factory BOM)
GIGA_CAP = re.compile(rf'^{NUM}([PNU])F?/(\d{{1,2}})(?:/(X5R|X7R|NPO|NP0|Y5V|X6S|C0G|[XYN]))?(?:/{NUM}V)?(?:/([BCDFGJKMZX]))?$', re.I)
GIGA_RES = re.compile(rf'^{NUM}([KMR]?)/(\d{{1,2}})(?:/(1|X))?$', re.I)
# older Gigabyte desktop boards put the voltage first: '0.1U/16V/X7R/4/X', '220P/50V/N/6'; inductors '10UH/8'
GIGA_CAP_VOLT_FIRST = re.compile(rf'^{NUM}([PNU])F?/{NUM}V/(X5R|X7R|NPO|NP0|Y5V|X6S|C0G|[XYN])/(\d{{1,2}})(?:/([BCDFGJKMZX]))?$', re.I)
GIGA_IND = re.compile(rf'^{NUM}(UH|NH|MH)/(\d{{1,2}})$', re.I)
# Tongfang (GK5CN5Z, PF4PN2F, CT4RVC1...): value-volts-size+dielectric-tolerance, value[-power][-tol]-size.
# Read off 14 boardviews (~20,000 labels): size 02/04/06/08/12 = 0201..1206 (or the 4-digit size); dielectric
# N only on <= 1nF 50V 5% parts (C0G), Y only with Z tolerance (Y5V), X on 25-50V pF-nF parts (X7R), R on
# low-voltage bulk parts (X5R). Lower-case m with a wattage on 1206 parts is milliohm; M on 0402 is megohm.
TF_DIEL = {'R': 'X5R', 'X': 'X7R', 'N': 'C0G', 'Y': 'Y5V'}
TF_CAP = re.compile(rf'^{NUM}([PNU])F?-{NUM}-(\d\d)([RXNY])(?:-([BCDFGJKMZ])\d?)?$', re.I)
TF_RES = re.compile(rf'^(THS-)?{NUM}([KMR]?)(?:-(\d+(?:/\d+)?)W)?(?:-{NUM})?-(\d\d|\d{{4}})$', re.I)
# MSI desktop boards: 1.5K/4, 0R/8, 6.04KT/4, 0.1u10X/4, 22u6.3X8, 0.22u6.3X4 (size digit after '/' or the
# dielectric letter; boardviews: /4 and X4 0402 in 832 of 837, /6 X6 0603, /8 X8 0805)
# Their tolerance and voltage forms, from 68 MSI boardviews (~60,000 labels): 5.1K1%4, 1.96KR1%/4, 15K/1%/4,
# 680R04, 2.2U16X6, C10U10X5/8, 1U/6.3V/4, 0.1U/16V/Y/4, 180P50N4; size digit 2 is 0402 too (1,150 of 1,160).
# The dielectric letter is left unread: no MSI factory BOM has confirmed it yet.
MSI_SIZED_CAP = re.compile(rf'^C?{NUM}([PNU])/?(?:{NUM}V?)?/?(?:[XYN][5-8]?)?/?(0[468]|[2468]|12)$', re.I)
MSI_SIZED_RES = re.compile(rf'^{NUM}([KM]?)R?T?/?(?:{NUM}%/?)?(0[468]|[2468]|12)$', re.I)
# Quanta: 2.2U/6.3V_4, .1U/10V_4X, 10P/50V_4; 1K/F_4, 34_4, 330_5%_2, 10K_2
QUANTA_CAP = re.compile(rf'^{NUM}([PNU])F?(?:/{NUM}V[A-Z]?)?_(\d{{1,2}})[A-Z]?$', re.I)
# Quanta jumpers: '*short_8', '*0/short_6', '*S_4' (a solder short, size code after it)
QUANTA_SHORT = re.compile(r'^(?:0/)?(?:SHORT|S)_(\d{1,2})$', re.I)
QUANTA_RES = re.compile(rf'^{NUM}([KMR]?)(?:/([FGJ])|_{NUM}%)?_(\d{{1,2}})$', re.I)
# Clevo: 0.22u_10V_X5R_04, 22u_6.3V_X6S_08; 100K_04, 10K_1%_04
CLEVO_CAP = re.compile(rf'^{NUM}([PNU])F?_{NUM}V_(X5R|X7R|X6S|X7S|C0G|NPO|NP0|Y5V)_(\d{{2}})$', re.I)
CLEVO_RES = re.compile(rf'^{NUM}([KMR]?)(?:_{NUM}%)?_(\d{{2}})$', re.I)
# Inventec: 1uF_6.3V_1, 330pF_50V_2, 0.1uF_16V_2_DY; 2K_5%_2, 10_1%_3
INVENTEC_CAP = re.compile(rf'^{NUM}([PNU])F_{NUM}V_(\d)(?:_DY)?$', re.I)
INVENTEC_RES = re.compile(rf'^{NUM}([KM]?)_{NUM}%_(\d)(?:_DY)?$', re.I)
# Wistron: SC1U10V2KX-1GP, SCD1U25V2KX-GP (D = decimal point: 0.1U), SC4D7U6D3V3KX-GP (4.7U 6.3V);
# 100KR2J-1-GP, 2K2R2J-2-GP (2.2K), 24K3R2F-1-GP (24.3K), 0R2J-2-GP
WISTRON_CAP = re.compile(r'^SC(D)?(\d+)(?:D(\d+))?([PNU])(\d+)(?:D(\d+))?V(\d)([BCDFGJKMZ])[A-Z]?-', re.I)
WISTRON_RES = re.compile(r'^(\d+)([KM]?)(\d*)R(\d)([FGJ])-', re.I)
# MSI writes the size out, so no ODM is needed: C0.1U25Y0402, C1U10X0603, C22P; 1KR0402, 0R0402,
# X_1KR1%0402-1, 33R, 330KR (the dielectric letters X/Y are not read: unchecked)
MSI_CAP = re.compile(rf'^C{NUM}([PNU])(\d+(?:\.\d)?)?(?:[XYN]\d?)?(\d{{4}})?$', re.I)
MSI_RES = re.compile(rf'^(?:X?_)?{NUM}([KM]?)R(\d+(?:\.\d+)?%)?(\d{{4}})?(?:-\d)?$', re.I)
# MSI server boards glue the size to the value and add a suffix or a resistor-network prefix:
# 47R0402-LF, 470R0402-RH, 33R0402-, 8P4R-47R0402 (8 pins, 4 resistors), X_10K0402, 4R70402 (4.7 ohm).
# Read on its own, the R would be taken for the decimal point ('47.0402 ohm'); the trailing
# imperial size says where the value ends.
MSI_RES_GLUED = re.compile(r'^(?:X?_)?(?:\d+P\d+R-)?(\d+)(?:([KM])R?|R)(\d{1,2})?(' + '|'.join(IMPERIAL) + r')(?:-[A-Z0-9]*)?$', re.I)
CAP_DIEL_WORDS = {'NPO': 'C0G', 'NP0': 'C0G'}


def detect_odm(text):
    """The ODM that drew a schematic, from words its pages carry, or None when the marks disagree."""
    counts = {name: len(re.findall(rx, text, re.I)) for name, rx in ODM_MARKS}
    best = max(counts, key=counts.get)
    ranked = sorted(counts.values(), reverse=True)
    return best if ranked[0] >= 2 and ranked[0] >= 3 * ranked[1] else None


def _odm_token(t, odm):
    """An ODM house format whose size code needs the ODM known: (kind, specs, package) or None."""
    size = ODM_SIZE.get(odm, {})
    if odm == 'quanta':
        m = QUANTA_CAP.match(t)
        if m and m.group(4) in size:
            spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6)}
            if m.group(3):
                spec['voltage_v'] = float(m.group(3))
            return 'capacitor', spec, size[m.group(4)]
        m = QUANTA_SHORT.match(t)
        if m and m.group(1) in size:
            return 'resistor', {'resistance_ohm': 0.0}, size[m.group(1)]
        m = QUANTA_RES.match(t)
        if m and m.group(5) in size:
            spec = {'resistance_ohm': _ohms(m.group(1), m.group(2))}
            if m.group(3):
                spec['tolerance'] = TOL_LETTER[m.group(3).upper()]
            elif m.group(4):
                spec['tolerance'] = f'{float(m.group(4)):g}%'
            return 'resistor', spec, size[m.group(5)]
    if odm == 'clevo':
        m = CLEVO_CAP.match(t)
        if m and m.group(5) in size:
            return 'capacitor', {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6),
                                 'voltage_v': float(m.group(3)),
                                 'dielectric': CAP_DIEL_WORDS.get(m.group(4).upper(), m.group(4).upper())}, size[m.group(5)]
        m = CLEVO_RES.match(t)
        if m and m.group(4) in size:
            spec = {'resistance_ohm': _ohms(m.group(1), m.group(2))}
            if m.group(3):
                spec['tolerance'] = f'{float(m.group(3)):g}%'
            return 'resistor', spec, size[m.group(4)]
    if odm == 'inventec':
        m = INVENTEC_CAP.match(t)
        if m and m.group(4) in size:
            return 'capacitor', {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6),
                                 'voltage_v': float(m.group(3))}, size[m.group(4)]
        m = INVENTEC_RES.match(t)
        if m and m.group(4) in size:
            return 'resistor', {'resistance_ohm': _ohms(m.group(1), m.group(2)),
                                'tolerance': f'{float(m.group(3)):g}%'}, size[m.group(4)]
    if odm == 'msi':
        m = MSI_SIZED_CAP.match(t)
        if m and m.group(4) in size:
            spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6)}
            if m.group(3):
                spec['voltage_v'] = float(m.group(3))
            return 'capacitor', spec, size[m.group(4)]
        m = MSI_SIZED_RES.match(t)
        if m and m.group(4) in size:
            spec = {'resistance_ohm': _ohms(m.group(1), m.group(2))}
            if m.group(3):
                spec['tolerance'] = f'{float(m.group(3)):g}%'
            return 'resistor', spec, size[m.group(4)]
    if odm == 'tongfang':
        m = TF_CAP.match(t)
        if m and m.group(4) in size:
            spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6),
                    'voltage_v': float(m.group(3)), 'dielectric': TF_DIEL[m.group(5).upper()]}
            if m.group(6):
                spec['tolerance'] = TOL_LETTER[m.group(6).upper()]
            return 'capacitor', spec, size[m.group(4)]
        m = TF_RES.match(t)
        if m and (m.group(6) in size or m.group(6) in IMPERIAL):
            mult = m.group(3)
            ohms = round(float(m.group(2)) * (1e-3 if mult == 'm' else {'': 1, 'R': 1, 'K': 1e3, 'M': 1e6}[mult.upper()]), 6)
            spec = {'resistance_ohm': ohms}
            if m.group(4):
                num, _, den = m.group(4).partition('/')
                spec['power_w'] = float(num) / float(den or 1)
            if m.group(5):
                spec['tolerance'] = f'{float(m.group(5)):g}%'
            return 'thermistor' if m.group(1) else 'resistor', spec, size.get(m.group(6), m.group(6))
    if odm == 'gigabyte':
        m = GIGA_CAP.match(t)
        if m and m.group(3) in size:
            spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6)}
            if m.group(4) and len(m.group(4)) > 1:
                spec['dielectric'] = {'NPO': 'C0G', 'NP0': 'C0G'}.get(m.group(4).upper(), m.group(4).upper())
            if m.group(5):
                spec['voltage_v'] = float(m.group(5))
            if m.group(6) and m.group(6).upper() != 'X':
                spec['tolerance'] = TOL_LETTER[m.group(6).upper()]
            return 'capacitor', spec, size[m.group(3)]
        m = GIGA_RES.match(t)
        if m and m.group(3) in size:
            spec = {'resistance_ohm': _ohms(m.group(1), m.group(2))}
            if m.group(4) == '1':
                spec['tolerance'] = '1%'
            return 'resistor', spec, size[m.group(3)]
        m = GIGA_CAP_VOLT_FIRST.match(t)
        if m and m.group(5) in size:
            spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6), 'voltage_v': float(m.group(3))}
            if len(m.group(4)) > 1:
                spec['dielectric'] = {'NPO': 'C0G', 'NP0': 'C0G'}.get(m.group(4).upper(), m.group(4).upper())
            if m.group(6) and m.group(6).upper() != 'X':
                spec['tolerance'] = TOL_LETTER[m.group(6).upper()]
            return 'capacitor', spec, size[m.group(5)]
        m = GIGA_IND.match(t)
        if m and m.group(3) in size:
            return 'inductor', {'inductance_uh': round(float(m.group(1)) * {'UH': 1, 'NH': 1e-3, 'MH': 1e3}[m.group(2).upper()], 6)}, size[m.group(3)]
    if odm == 'wistron':
        m = WISTRON_CAP.match(t)
        if m and m.group(7) in size:
            whole = '0' if m.group(1) else m.group(2)
            frac = m.group(2) if m.group(1) else (m.group(3) or '')
            value = float(f'{whole}.{frac}' if frac else whole)
            volt = float(f'{m.group(5)}.{m.group(6)}' if m.group(6) else m.group(5))
            return 'capacitor', {'capacitance_pf': round(value * UNIT_PF[m.group(4).upper()], 6), 'voltage_v': volt,
                                 'tolerance': TOL_LETTER[m.group(8).upper()]}, size[m.group(7)]
        m = WISTRON_RES.match(t)
        if m and m.group(4) in size:
            v = float(f'{m.group(1)}.{m.group(3)}' if m.group(3) else m.group(1))
            return 'resistor', {'resistance_ohm': round(v * {'': 1, 'K': 1e3, 'M': 1e6}[m.group(2).upper()], 6),
                                'tolerance': TOL_LETTER[m.group(5).upper()]}, size[m.group(4)]
    return None


NOT_FITTED = re.compile(r'^\*|^@$')
VARIANT = re.compile(r'^([A-Z0-9]+)@', re.I)
IC_PN = re.compile(r'^(?=.*\d)(?=.*[A-Z])[A-Z0-9][A-Z0-9-]{5,}$')
SAME_KIND = {('inductor', 'ferrite'), ('ferrite', 'inductor'), ('resistor', 'thermistor')}


def designator_kind(designator):
    return next((k for pattern, k in DESIGNATOR_KIND if re.match(pattern, designator or '', re.I)), None)


def _ohms(num, mult):
    return round(float(num) * {'': 1, 'R': 1, 'K': 1e3, 'M': 1e6}[mult.upper()], 6)


# a bracket _clean keeps: one holding a size or a rated field ('电阻0R(0402-0.0625W-J)', 'F(±1%)',
# '(0201_X5R_6.3V_K)'); others are codes, pin names, page references or formulas ('(0K445)', '1(G)', '(30)')
BRACKET_FIELDS = re.compile(r'(?<!\d)(?:' + '|'.join(IMPERIAL) + r')(?!\d)|\d(?:V|W)\b|%|X[5-8][RSTP]|C0G|COG|NP0',
                            re.I)


DATE = re.compile(r'(19|20)\d\d[/.-]\d{1,2}[/.-]\d{1,2}')


def _bracket(m):
    inner = m.group(1)
    if DATE.fullmatch(inner.strip()):
        return ' '                              # a revision date: '(2010/11/24)'
    if inner in IMPERIAL:
        return f' {inner} '                     # '(0603)X5R': the size
    return m.group(0) if BRACKET_FIELDS.search(inner) else ' '


def _clean(token):
    """(token without stuffing/variant marks and Compal's '~D' tail, flags)."""
    flags = []
    t = token.strip()
    if '(' in t:
        # a bracketed code is not the label's value (Asus '37.4 1%(0K445)' is 37.4 ohms, per its factory BOM)
        t = re.sub(r'\(([^()]*)\)', _bracket, t).strip()
    if DATE.fullmatch(t):
        t = ''                                  # a revision date ('2008/08/11') is not 2008 ohms
    if t.endswith('~D'):
        t = t[:-2]
    if t.upper().endswith('_DY'):                   # Inventec's mark on parts not fitted (dummy)
        flags.append('not fitted by default')
        t = t[:-3]
    if t.upper().endswith('_NC'):                   # Quanta, Dell: '*10K_1%_2_NC' - not connected
        flags.append('not fitted by default')
        t = t[:-3]
    if t.upper().endswith('/S'):                    # Quanta '*0_2/S'
        t = t[:-2]
    if t[:2].upper() == 'X_' and len(t) > 3:        # MSI 'x_15k/4': a build option
        flags.append('build option (X_): may not be fitted')
        t = t[2:]
    if t.startswith('@') and len(t) > 1:            # Tongfang's leading mark ('@10K-04'): a build option
        flags.append('build option (@): may not be fitted')
        t = t[1:]
    if NOT_FITTED.search(t):
        flags.append('not fitted by default')
        t = t.strip('*@')
    m = VARIANT.match(t)
    if m:
        flags.append(f'fitted in build {m.group(1).upper()} only')
        t = t[m.end():]
    return t, flags


# a label listing the approved makers' part numbers (Acer/Wistron boards):
# 'C0201X5R105M6R3NTX~~CL03A105MQ3CSNH~~GRM033R60J105MEA2D', '0201WMJ0103TCE+0201WMJ0103TJE~~RC0201JR-0710KL'
APPROVED_SPLIT = re.compile(r'~~|\+')
# a footprint name printed as a part attribute (Asus/Pegatron): VX_R0402_SMALL, NBS_C0402_H22_000S, R0402_H16
FOOTPRINT_WORD = re.compile(r'^(?:[A-Z]{2,3}_)?([RCL])(01005|0201|0402|0603|0805|1206|1210|2512)(?:_[A-Z0-9]+)+$|'
                            r'^[A-Z]{2,3}_([RCL])(01005|0201|0402|0603|0805|1206|1210|2512)$', re.I)


# Compal/LCFC chips and discretes: part number, '_', package with its pin count ('AP7175SP-13_SO-8EP-8',
# '2N7002K_SOT23-3', 'AON7408L_DFN8-5', 'F75397M_MSOP8')
PN_PACKAGE = re.compile(r'^([A-Z0-9][A-Z0-9.+/-]{3,})_((?:SO|SOT|TSOT|SOD|SOP|SSOP|TSSOP|MSOP|QFN|UQFN|VQFN|DFN|WDFN|UDFN|'
                        r'TDFN|VDFN|PDFN|SON|WSON|USON|SC|TO|LGA|BGA|WLCSP|CSP|QFP|LQFP|TQFP|PLCC|SMA|SMB|SMC)'
                        r'-?\d[\w-]*)$', re.I)
# pin counts a package name already implies: 'SOT23-3' is the site's 'SOT-23'
IMPLIED_PINS = {'SOT23': '3', 'SOT323': '3', 'SOT353': '5', 'SOT363': '6', 'SOT523': '3', 'SOT563': '6', 'SOT89': '3',
                'SOT223': '4', 'SOT143': '4', 'SC70': '3', 'SOD123': '2', 'SOD323': '2', 'SOD523': '2', 'TO252': '3',
                'TO263': '3'}


def _pn_package(t):
    """(part number, package in the site's style) for a part-number_package label, or None."""
    from apps.components.spec_parse import ic_package
    m = PN_PACKAGE.match(t)
    if not m:
        return None
    pkg = m.group(2).upper()
    base, _, pins = pkg.rpartition('-') if re.search(r'-\d+$', pkg) else (pkg, '', '')
    if IMPLIED_PINS.get(base.replace('-', '')) == pins or (pins and re.search(rf'(?<!\d){pins}(?!\d)', base)):
        pkg = base                          # 'SO-8EP-8': the 8 is in the name already
    return m.group(1).upper(), ic_package(pkg) or pkg


# crystal labels: '25MHZ_18PF_7V25000034', '27mhz20p_d' (MSI), 'XTAL-32D768KHZ-65-GP' (Wistron, D the point),
# '38.4MHZ/10ppm' (Quanta), '32.768K-12.5-20-CM315' (Tongfang: frequency-load-ppm)
XTAL_FREQ = re.compile(r'(?<![\d.])(\d+(?:[.D]\d+)?)\s*(MHZ|KHZ)', re.I)
XTAL_TONGFANG = re.compile(r'^(\d+(?:\.\d+)?)(M|K)-(\d+(?:\.\d+)?)-(\d+)(?:-|$)', re.I)


def _crystal(t):
    """(specs) for a crystal label, or None: frequency, and the load and ppm when printed."""
    m = XTAL_TONGFANG.match(t)
    if m:
        f = float(m.group(1)) / (1 if m.group(2).upper() == 'M' else 1000)
        return {'frequency_mhz': round(f, 6), 'load_pf': float(m.group(3)), 'tolerance_ppm': int(m.group(4))}
    m = XTAL_FREQ.search(t)
    if not m:
        return None
    f = float(m.group(1).upper().replace('D', '.')) / (1 if m.group(2).upper() == 'MHZ' else 1000)
    spec = {'frequency_mhz': round(f, 6)}
    rest = t[m.end():]
    load = re.match(r'[\s_/-]*(\d+(?:\.\d+)?)\s*P(?:F)?(?![A-Z])', rest, re.I)
    if load:
        spec['load_pf'] = float(load.group(1))
    ppm = re.search(r'(\d+)\s*PPM', t, re.I)
    if ppm:
        spec['tolerance_ppm'] = int(ppm.group(1))
    return spec


# label words that look like net names ('x_15k/4', 'short_8') but are a build option or a jumper
PREFIXED_LABEL = re.compile(r'^\*?(?:0/)?(?:SHORT|S)_\d{1,2}$|^X_C?\.?\d', re.I)     # MSI 'x_c0.1u16y0402' too


def _approved_list(t):
    """The first maker part number in the list whose maker's scheme gives the value."""
    for piece in APPROVED_SPLIT.split(t):
        piece = piece.strip().upper()
        maker = guess_maker(piece)
        decoded = decode_mpn(maker, piece) if maker else None
        if decoded and any(k in decoded[1] for k in VALUE_KEYS):
            return decoded[0], dict(decoded[1]), decoded[2], (maker, piece)
    return None


# a Chinese house style (graphics cards, phone boards): the part type in words, then value, size and
# ratings split by '_' or bracketed - '电阻_20K_0201_1/20W_J', '电容_1uF_0201_X5R_6.3V_M',
# '电阻0R(0402-0.0625W-J)', '电阻_39欧姆_0201_1/20W_F(±1%)'. 电阻 resistor, 电容 capacitor, 电感 inductor,
# 贴片功率电感器 SMD power inductor, 磁珠 ferrite bead; 欧姆 / Ω ohm, 毫欧 milliohm
CN_LABEL = re.compile(r'^(贴片功率电感器|电阻|电容|电感|磁珠)_?(.+)$')
CN_KIND = {'电阻': 'resistor', '电容': 'capacitor', '电感': 'inductor', '贴片功率电感器': 'inductor', '磁珠': 'ferrite'}
CN_DIELECTRIC = {'X5R': 'X5R', 'X7R': 'X7R', 'X6S': 'X6S', 'X7S': 'X7S', 'C0G': 'C0G', 'COG': 'C0G', 'NP0': 'C0G',
                 'NPO': 'C0G', 'Y5V': 'Y5V'}
CN_VOLTS = (4, 6.3, 10, 16, 25, 35, 50, 63, 100, 200, 250)     # a bare number after the size: '电容_100nF_0201_16'


def _cn_label(t):
    m = CN_LABEL.match(t.replace('（', '(').replace('）', ')'))
    if not m:
        return None
    kind = CN_KIND[m.group(1)]
    rest = re.sub(r'\(?±[\d.]+%\)?', '', m.group(2))                # 'F(±1%)': the letter says it already
    rest = re.sub(r'([KM])(?:Ω|欧姆|OHM)', r'\1', rest, flags=re.I)        # '22KΩ', '18K欧姆'
    rest = rest.replace('毫欧', 'MOHM').replace('欧姆', 'R').replace('Ω', 'R')
    fields = [f for f in re.split(r'[_(),\-\s]|(?<!\d)/|/(?!\d+W?(?:[_(),\-\s]|$))', rest.upper()) if f]   # '1/20W' is one field, '0402/5%' two
    if not fields:
        return None
    specs, package = {}, None
    v = fields[0].upper()
    if kind == 'resistor':
        r = re.fullmatch(r'(\d*\.?\d+)(MOHM|OHM|[RKM]?)(\d*)', v)
        if not r or (r.group(3) and r.group(2) not in 'RKM'):
            return None
        num = float(r.group(1) + ('.' + r.group(3) if r.group(3) else ''))
        specs['resistance_ohm'] = round(num * {'': 1, 'R': 1, 'OHM': 1, 'K': 1e3, 'M': 1e6, 'MOHM': 1e-3}[r.group(2)], 6)
    elif kind == 'capacitor':
        c = re.fullmatch(r'(\d*\.?\d+)([PNU])F?', v)
        if not c:
            return None
        specs['capacitance_pf'] = round(float(c.group(1)) * UNIT_PF[c.group(2)], 6)
    elif kind == 'inductor':
        i = re.fullmatch(r'(\d*\.?\d+)([NU])H', v)
        if not i:
            return None
        specs['inductance_uh'] = float(i.group(1)) * (1e-3 if i.group(2) == 'N' else 1)
    else:
        b = re.fullmatch(r'(\d*\.?\d+)R(?:@?/?100MHZ)?', v)
        if not b:
            return None
        specs['impedance_ohm'] = float(b.group(1))
    for f in (x.upper() for x in fields[1:]):
        size = re.fullmatch(r'C{0,2}(\d{4,5})', f)
        if size and size.group(1) in IMPERIAL:
            package = package or size.group(1)
        elif f in CN_DIELECTRIC and kind == 'capacitor':
            specs['dielectric'] = CN_DIELECTRIC[f]
        elif (w := re.fullmatch(r'(\d+)/(\d+)W?', f)) and kind == 'resistor':
            specs['power_w'] = round(int(w.group(1)) / int(w.group(2)), 6)
        elif (w := re.fullmatch(r'(\d*\.?\d+)W', f)) and kind == 'resistor':
            specs['power_w'] = float(w.group(1))
        elif (u := re.fullmatch(r'(\d*\.?\d+)V?', f)) and kind == 'capacitor' and 'dielectric' in specs \
                and 'voltage_v' not in specs:
            specs['voltage_v'] = float(u.group(1))           # after the dielectric a bare number is the voltage
        elif (u := re.fullmatch(r'(\d*\.?\d+)V', f)) and kind == 'capacitor' or \
                (u := re.fullmatch(r'(\d*\.?\d+)', f)) and kind == 'capacitor' and package \
                and float(u.group(1)) in CN_VOLTS and 'voltage_v' not in specs:
            specs['voltage_v'] = float(u.group(1))
        elif f in TOL_LETTER and kind in ('resistor', 'capacitor') and 'tolerance' not in specs \
                and (kind == 'capacitor' or f in 'DFGJ'):
            specs['tolerance'] = TOL_LETTER[f] if f != 'D' or kind == 'capacitor' else '0.5%'
        elif (p := re.fullmatch(r'(\d*\.?\d+)%', f)) and 'tolerance' not in specs:
            specs['tolerance'] = f'{float(p.group(1)):g}%'
        elif (p := re.fullmatch(r'±(\d*\.?\d+)PF', f)) and kind == 'capacitor':
            specs['tolerance'] = f'±{float(p.group(1)):g}pF'
    if specs.get('voltage_v') is not None and specs['voltage_v'] == int(specs['voltage_v']):
        specs['voltage_v'] = int(specs['voltage_v'])
    return kind, specs, package


def parse_token(token, kind=None, odm=None):
    """One label word -> (kind, specs, package, (maker, part number) or None), or None."""
    t, _ = _clean(token)
    cn = _cn_label(t)
    if cn:
        return (*cn, None)
    if odm != 'wistron' and re.search(r'-?\d?GP$', t, re.I) and (WISTRON_CAP.match(t) or WISTRON_RES.match(t)):
        odm = 'wistron'                     # Wistron's own codes ('SCD1U16V2KX-3GP') say who drew them
    try:
        r = _odm_token(t, odm) if odm in ODM_SIZE else None
    except (KeyError, ValueError):          # a code outside the ODM's table: leave the word unread
        r = None
    if r:
        return (*r, None)
    if '~~' in t:
        r = _approved_list(t)
        if r:
            return (SITE_TYPE.get(r[0], r[0]), *r[1:])
    if kind == 'crystal':
        spec = _crystal(t)
        if spec:
            return 'crystal', spec, None, None
    if kind not in ('resistor', 'capacitor', 'inductor', 'ferrite', 'thermistor'):
        r = _pn_package(t)
        if r:
            maker = guess_maker(r[0])
            return None, {}, r[1], (maker, r[0])
    m = MSI_CAP.match(t)
    if m and (m.group(3) or m.group(4)):
        spec = {'capacitance_pf': round(float(m.group(1)) * UNIT_PF[m.group(2).upper()], 6)}
        if m.group(3):
            spec['voltage_v'] = float(m.group(3))
        return 'capacitor', spec, m.group(4) if m.group(4) in IMPERIAL else None, None
    m = MSI_RES.match(t)
    if m and kind in (None, 'resistor') and (m.group(3) or m.group(4) or m.group(2)):
        spec = {'resistance_ohm': _ohms(m.group(1), m.group(2))}
        if m.group(3):
            spec['tolerance'] = m.group(3)
        return 'resistor', spec, m.group(4) if m.group(4) in IMPERIAL else None, None
    m = MSI_RES_GLUED.match(t)
    if m and kind in (None, 'resistor'):
        number = f'{m.group(1)}.{m.group(3)}' if m.group(3) else m.group(1)
        return 'resistor', {'resistance_ohm': _ohms(number, m.group(2) or '')}, m.group(4), None
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
    joined = re.sub(r'(?<![\d.])(\d+)/(\d+)W', lambda m: f'{int(m.group(1)) / int(m.group(2)):g}W', ' '.join(words), flags=re.I)
    parts = re.sub(r'[_/,]', ' ', joined).split()   # '0.1U/10V_4X', '0.22uF/16V,X7R'; '1/16W' kept as 0.0625W
    # after the value, a bare one- or two-digit word is an ODM's size code ('34_4', '*0_04'), not a value
    text = ' '.join(parts[:1] + [w for w in parts[1:] if not re.fullmatch(r'\d{1,2}', w)])
    k, specs, pkg = parse_description(text, kind or '')
    specs = dict(specs)
    first = text.split()[0] if text.split() else ''
    if kind in ('resistor', 'thermistor') and 'resistance_ohm' not in specs:
        m = re.fullmatch(r'(\d*\.?\d+)([KMR]?)(\d*)', first, re.I)        # '34', '10K', '4K7', '1M'
        if first in IMPERIAL:
            m = None                        # '0402 5%': the size, not 402 ohms
        if m and not (m.group(3) and (not m.group(2) or '.' in m.group(1) or len(m.group(3)) > 3)):
            v = float(m.group(1) + ('.' + m.group(3) if m.group(3) else ''))
            specs['resistance_ohm'] = round(v * {'': 1, 'R': 1, 'K': 1e3, 'M': 1e6}[m.group(2).upper()], 6)
        letter = next((w for w in text.split()[1:] if re.fullmatch(r'[FGJ]', w, re.I)), None)
        if letter and 'tolerance' not in specs:
            specs['tolerance'] = TOL_LETTER[letter.upper()]           # EIA letter: '1K/F_4' is 1%
    if not specs and not pkg:
        return None
    return SITE_TYPE.get(k, k) if k else kind, specs, pkg, None


# a value written in brackets ('(4K7)', '1%(0K445)', '(0.1UF)'): a number with a unit or multiplier letter,
# so page references ('(36,38)') and three-digit codes ('(473)') are not taken for one
BRACKETED_VALUE = re.compile(r'\((\d*\.?\d+[KMRUNP]\w*)\)', re.I)


def parse_label(tokens, designator, odm=None):
    """Words gathered around one designator -> {'kind', 'specs', 'package', 'maker', 'part_number',
    'flags', 'confidence', 'used'}. confidence: 'high' when a known label format gives the value and the
    designator agrees on the kind, 'medium' when only some fields could be read, 'low' when none."""
    out = _parse_label(tokens, designator, odm)
    if any(k in out['specs'] for k in VALUE_KEYS) or out['part_number']:
        return out
    # brackets are dropped from a word ('37.4 1%(0K445)' is 37.4 ohms, per Asus's factory BOMs), but a
    # bracketed value is the label's only one when nothing else gives a value
    inner = [v for t in tokens for v in BRACKETED_VALUE.findall(t)]
    if not inner:
        return out
    alt = _parse_label(inner + list(tokens), designator, odm)
    if not any(k in alt['specs'] for k in VALUE_KEYS):
        return out
    alt['flags'].append('value read from a bracketed code')
    alt['confidence'] = 'medium'
    return alt


def _parse_label(tokens, designator, odm):
    want = designator_kind(designator)
    flags = sorted({f for t in tokens for f in _clean(t)[1]})
    found, used, other = [], [], []
    for t in tokens:
        r = parse_token(t, want, odm)
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
    if has_value and not clash and agrees and (used or fields >= 3) and (out['maker'] or not out['part_number']
                                                                        or want in ('resistor', 'capacitor')):
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
    if kind == 'crystal' and 'frequency_mhz' in s:
        f = s['frequency_mhz']
        freq = f'{f:g}MHz' if f >= 1 else f'{f * 1000:g}kHz'
        load = f"{s['load_pf']:g}pF" if s.get('load_pf') else ''
        ppm = f"{s['tolerance_ppm']}ppm" if s.get('tolerance_ppm') else ''
        return ' '.join(x for x in ('XTAL', freq, load, ppm, pkg) if x)
    if kind == 'thermistor' and 'resistance_ohm' in s:
        return ' '.join(x for x in ('NTC', _fmt_ohm(s['resistance_ohm']), s.get('tolerance', ''), pkg) if x)
    return None
