"""
Read a component's ratings out of its description text and its part number.

Bulk imports (factory BOMs, service-manual parts lists, contributor lists)
put everything in the description: "P MLCC 15PF/50V (0402) NPO 5%
TAIYO/UMK105CH150JW-F", "C-CER,CHIP;1000nF,10%,6.3V,X7R,1608", "Metal film
chip resistor, ±1% tolerance, 1/4W". parse_description() turns that into
Component.specifications keys (the ones primary_value and value_search read)
plus a package. decode_mpn() reads the same ratings from part numbers whose
maker's numbering scheme fixes them (YAGEO RC/CC, Murata GRM, ...), and
derive() combines the two: a description is only trusted where the part
number, when decodable, agrees with it.

No Django imports: also used by scripts outside the site.
"""
import re
from fractions import Fraction

# ---- canonical keys ----------------------------------------------------------
# value keys by kind; everything else is a rating
RATING_KEYS = ('voltage_v', 'power_w', 'current_a', 'tolerance', 'dielectric', 'load_pf', 'tolerance_ppm',
               'impedance_ohm', 'frequency_mhz', 'b_value_k', 'configuration')

IMPERIAL = ('01005', '0201', '0402', '0603', '0805', '1008', '1206', '1210', '1806', '1812', '2010', '2512')
CAP_CASES = ('3216', '3528', '6032', '7343')     # tantalum / polymer chip cases (EIA metric)
METRIC_TO_IMPERIAL = {'1005': '0402', '1608': '0603', '2012': '0805', '3216': '1206', '3225': '1210',
                      '4516': '1806', '4532': '1812', '5025': '2010', '6332': '2512'}
DIELECTRICS = {'NPO': 'C0G', 'NP0': 'C0G', 'COG': 'C0G', 'C0G': 'C0G', 'X7R': 'X7R', 'X5R': 'X5R', 'Y5V': 'Y5V',
               'Z5U': 'Z5U', 'X6S': 'X6S', 'X7S': 'X7S', 'X8R': 'X8R', 'X7T': 'X7T', 'CH': 'CH', 'SL': 'SL'}
TOL_LETTER = {'B': '±0.1pF', 'C': '±0.25pF', 'D': '±0.5pF', 'F': '1%', 'G': '2%', 'J': '5%', 'K': '10%',
              'M': '20%', 'Z': '+80/-20%'}
IC_PACKAGE = re.compile(
    r'(?<![A-Z0-9])(S-\d{1,2}|SO-?\d{1,2}P?|SOIC-?\d{1,2}|T?SSOP-?\d{1,2}|MSOP-?\d{1,2}|SOP-?\d{1,2}|'
    r'[TL]?QFP-?\d{2,3}|[VW]?QFN-?\d{1,2}|DFN-?\d{1,2}|PLCC-?\d{2}|[PF]?BGA-?\d{2,4}|SOT-?\d{2,3}(?:-\d)?|'
    r'SOD-?\d{2,3}|SC-?70(?:-\d)?|TO-?\d{2,3}[A-Z]?(?:-\d)?|D2?PAK|DIP-?\d{1,2}|SMA|SMB|SMC|MELF|'
    r'S-TO\d{3})(?![A-Z0-9])')

# ---- text normalisation --------------------------------------------------------
ECHO = re.compile(r'\s*\b(?:TAI TECH|TAIYO YUDEN|[A-Z][A-Z0-9&.-]*)/(?=[A-Z0-9#._+-]*\d)[A-Z0-9][A-Z0-9#._+/-]*\s*$')
MARKERS = re.compile(r'\s*<G>|\s*(?:phantom item|虛擬料件)\s*[:：]?\s*\S*', re.I)


def clean_bom_text(text):
    """Factory BOM line without the plant marker ('P '), the green marker ('<G>'),
    'phantom item: 59-...' and the trailing MAKER/PART echo: 'P MLCC 15PF/50V (0402)
    NPO 5% TAIYO/UMK105CH150JW-F <G>' -> 'MLCC 15PF/50V (0402) NPO 5%'."""
    t = re.sub(r'\s+', ' ', (text or '').strip())
    t = re.sub(r'^P\s+(?=\S)', '', t)
    t = MARKERS.sub('', t).strip()
    for _ in range(2):                       # 'X/PN<G>' and an occasional second echo
        t = ECHO.sub('', t).strip()
    return t


def _norm(text):
    t = clean_bom_text(text)
    t = (t.replace('Ω', ' OHM').replace('µ', 'U').replace('μ', 'U').replace('+/-', '±').replace('+-', '±')
         .replace('，', ',').replace('；', ';'))
    return t


def _num(s):
    return float(s.replace(',', '.'))


# ---- kind ----------------------------------------------------------------------
# (kind, head: the text starts with it, anywhere: the text names it somewhere)
KINDS = [
    ('res_array', r'^(RES\.? ?A\b|R\.? ?ARRAY|RES\.? ?ARRAY|CHIP RES\.? ?ARRAY|RN\b|R-NET|RES(ISTOR)?[ -]NETWORK)',
     r'RESISTOR NETWORK|\b\dR\dP\b'),
    ('thermistor', r'^(THERMISTOR|NTC\b|PTC\b)', r'\bTHERMISTOR\b'),
    ('varistor', r'^VARISTOR', r'\bVARISTOR\b'),
    ('fuse', r'^(POLYSWITCH|FUSE\b(?! ?HOLDER| ?CLIP)|POLYFUSE)', r'\bFUSE\b(?! ?HOLDER| ?CLIP)|\bPOLYSWITCH\b'),
    ('resistor', r'^(RES\b|RES\.|R-CHIP|R\.CHP|R-CARBON|R-METAL|RST\b|CHIP RES|CHIP RESISTOR|RESISTOR)',
     r'\bRESISTORS?\b'),
    ('cm_choke', r'^(C\.? ?M\.? ?CHOKE|COMMON[ -]MODE|COMMON CHOKE|CM CHOKE)', r'COMMON MODE CHOKE'),
    ('ferrite', r'^(FERRITE|BEAD|CORE-FERRITE)', r'\bFERRITE BEAD\b|\bCHIP BEAD\b'),
    ('inductor', r'^(INDUCTOR|CHOKE|COIL|L-CHIP|IND\b|CHIP INDUCT)', r'\bINDUCTORS?\b|\bINDUCTANCE\b'),
    ('capacitor', r'^(MLCC|CAP\b|CAP\.|CHIP CAP|SMD CAP|E/C|EC CAP|C-CER|C-AL|C-TA|C-FILM|C-MYLAR|C\.(MYLAR|CE|EL|TA)|'
                  r'CER\.? ?CAP|ELEC\.? ?CAP)', r'CAPACITORS?\b|\bELECTROLYTIC\b'),
    ('crystal', r'^(XTAL|CRYSTAL|CRYSTAL-SMD|RESONATOR|OSC\b|OSCILLATOR)', r'\bCRYSTALS?\b'),
]
# 'CRYSTAL CS4297A-JQ TQFP48 AC97 AUDIO CODEC': Crystal Semiconductor, the maker - not a crystal
NOT_A_CRYSTAL = re.compile(r'CODEC|AUDIO|\bAC97\b|\b[TL]?QFP|\bSSOP|\bSOIC|\bPLCC|\bCS\d{3,}')


def kind_of(text, head_only=False):
    """The passive kind a description names, or None. head_only: only when the text starts
    with it ('R-CHIP;...', 'MLCC ...'), not when it merely mentions it."""
    u = _norm(text).upper()
    for kind, head, anywhere in KINDS:
        if re.search(head, u) or (not head_only and re.search(anywhere, u)):
            if kind == 'crystal' and NOT_A_CRYSTAL.search(u) and not re.search(r'\d\s*[MK]HZ', u):
                continue
            return kind
    return None


SITE_TYPE = {'res_array': 'resistor', 'resistor': 'resistor', 'thermistor': 'thermistor', 'varistor': 'other',
             'fuse': 'fuse', 'cm_choke': 'inductor', 'ferrite': 'ferrite', 'inductor': 'inductor',
             'capacitor': 'capacitor', 'crystal': 'crystal'}
TYPE_KIND = {'resistor': 'resistor', 'capacitor': 'capacitor', 'inductor': 'inductor', 'ferrite': 'ferrite',
             'crystal': 'crystal', 'thermistor': 'thermistor', 'fuse': 'fuse'}


# ---- quantities ----------------------------------------------------------------
def _package(u):
    """Imperial chip size, from an imperial code or a metric one ('1608' -> '0603')."""
    for m in re.finditer(r'(?<![\d.*xX×])(\d{4,5})(?:/[A-Z])?(?![\d.*xX×])', u):
        code = m.group(1)
        if code in IMPERIAL:
            return code
        if code in METRIC_TO_IMPERIAL:
            return METRIC_TO_IMPERIAL[code]
    return None


def _tolerance(u, kind=None):
    pfs = list(re.finditer(r'(±)?\s*(\d*\.?\d+)\s*PF\b', u))
    if kind == 'capacitor' and len(pfs) >= 2 and _num(pfs[-1].group(2)) <= 1:
        return f'±{_num(pfs[-1].group(2)):g}pF'
    if kind == 'capacitor' and pfs and pfs[-1].group(1):
        return f'±{_num(pfs[-1].group(2)):g}pF'           # 'Tol 0.1pF' style handled below
    if re.search(r'\+\s*80\s*%?\s*[/,]?\s*-\s*20|-\s*20\s*%?\s*[/,]?\s*\+\s*80|-\s*80\s*%?\s*\+\s*20\s*%', u):
        return '+80/-20%'
    m = re.search(r'(?:±|TOL\.?\s*)\s*(\d+(?:\.\d+)?)\s*%', u) or re.search(r'(?<![\d.(])(\d+(?:\.\d+)?)\s*%(?!\))', u)
    if m:
        return f'{float(m.group(1)):g}%'
    if kind == 'capacitor':
        m = re.search(r'\bTOL\.?\s*(\d*\.?\d+)\s*PF\b', u)
        if m:
            return f'±{_num(m.group(1)):g}pF'
    return None


def _power(u):
    m = re.search(r'(?<![\d.])(\d+/\d+|\d+(?:\.\d+)?)\s*(M?W)\b', u)
    if not m:
        return None
    v = float(Fraction(m.group(1))) if '/' in m.group(1) else _num(m.group(1))
    return round(v / 1000, 6) if m.group(2) == 'MW' else v


def _current(u):
    m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(MA|A)(?:DC)?\b', u)
    if not m:
        return None
    return round(_num(m.group(1)) / (1000 if m.group(2) == 'MA' else 1), 6)


def _voltage(u):
    m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*KV\b', u)
    if m:
        return _num(m.group(1)) * 1000
    m = (re.search(r'/\s*(\d+(?:\.\d+)?)\s*V(?:DC)?\b', u)
         or re.search(r'(?<![\d.\-])(\d+(?:\.\d+)?)\s*V(?:DC|AC)?\b(?!\s*-)', u)
         or re.search(r'\b(?:AC|DC)\s*(\d+(?:\.\d+)?)\s*V\b', u))
    return _num(m.group(1)) if m else None


def _ohms(u, raw):
    """Resistance in ohms. 'm' (lower case, in mixed-case text) is milli; 'M' is mega."""
    for m in re.finditer(r'(?<![\d.])(\d+(?:\.\d+)?)\s*([KkMmR]?)\s*OHMS?\b', raw, re.I):
        p = m.group(2)
        mult = {'': 1, 'R': 1, 'r': 1, 'K': 1e3, 'k': 1e3, 'M': 1e6}.get(p)
        if p == 'm':
            mult = 1e-3 if raw != raw.upper() else 1e6
        return round(_num(m.group(1)) * mult, 6)
    m = re.search(r'(?<![\dA-Z.])(\d+)([KMR])(\d+)(?![\dA-Z])', u)          # EIA: 4K7, 4R7, 1M5
    if m:
        return round(float(f'{m.group(1)}.{m.group(3)}') * {'K': 1e3, 'M': 1e6, 'R': 1}[m.group(2)], 6)
    return None


def _bare_ohms(u):
    """'RST CHIP 1K 1/16W', 'Chip Resistor, 100 1/10W', 'Metal Oxide 6.2k 1/16W': first bare
    number (optionally K/M) that isn't a size code, a fraction, a percentage or a rating."""
    for m in re.finditer(r'(?<![\d./A-Z-])(\d+(?:\.\d+)?)\s*([KMR]?)(?![\d./%A-Z])', u):
        if m.group(1) in IMPERIAL or m.group(1) in METRIC_TO_IMPERIAL:
            continue
        return round(_num(m.group(1)) * {'': 1, 'R': 1, 'K': 1e3, 'M': 1e6}[m.group(2)], 6)
    return None


def _farads_pf(u):
    m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(PF|NF|UF|P|N|U)(?![A-Z0-9])', u)
    if not m:
        return None
    mult = {'P': 1, 'PF': 1, 'N': 1e3, 'NF': 1e3, 'U': 1e6, 'UF': 1e6}[m.group(2)]
    return round(_num(m.group(1)) * mult, 6)


def _henries_uh(u):
    m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(UH|NH|MH)\b', u)
    if not m:
        return None
    return round(_num(m.group(1)) * {'NH': 1e-3, 'UH': 1, 'MH': 1e3}[m.group(2)], 6)


def _hertz_mhz(u):
    m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(MHZ|KHZ|GHZ)\b', u)
    if not m:
        return None
    return round(_num(m.group(1)) * {'KHZ': 1e-3, 'MHZ': 1, 'GHZ': 1e3}[m.group(2)], 9)


# ---- description -> specs -------------------------------------------------------
def parse_description(text, component_type=''):
    """(kind, specs, package) read from a description; kind None when it names no passive.
    The kind comes from the text itself; component_type only decides when the text is
    a bare value list ('0.1uF/100V, X7R')."""
    raw = _norm(text)
    if not raw:
        return None, {}, None
    u = raw.upper()
    kind = kind_of(raw) or TYPE_KIND.get(component_type)
    if not kind:
        return None, {}, None
    s = {}
    package = _package(u)
    if kind in ('resistor', 'res_array'):
        ohms = _ohms(u, raw)
        if ohms is None and kind == 'resistor':
            ohms = _bare_ohms(re.sub(r'^\S+', '', u))     # skip the head word ('R-CHIP;', 'RST')
        s['resistance_ohm'] = ohms
        s['tolerance'] = _tolerance(u, kind)
        s['power_w'] = _power(u)
        if kind == 'res_array':
            m = re.search(r'\b(\d+)R(\d+)P\b', u)
            s['configuration'] = f'{m.group(1)}R{m.group(2)}P' if m else None
            if package:
                s['size_on_bom'] = package     # Asus gives the element size; the body is bigger
                package = None
        if ohms == 0 or 'JUMP' in u:
            s = {'resistance_ohm': 0.0}
    elif kind == 'capacitor':
        s['capacitance_pf'] = _farads_pf(u)
        s['voltage_v'] = _voltage(u)
        s['tolerance'] = _tolerance(u, kind)
        if not s['tolerance']:
            m = re.search(r'\d\s*(?:PF|NF|UF)\s+([BCDFGJKMZ])\b', u)       # 'CAP CHIP 0402 470PF J 50V'
            s['tolerance'] = TOL_LETTER.get(m.group(1)) if m else None
        for tok, name in DIELECTRICS.items():
            if re.search(rf'(?<![A-Z0-9]){tok}(?![A-Z0-9])', u):
                s['dielectric'] = name
                break
        if re.search(r'\b(TANT|TAN\b|C-TA|C\.TA)', u):
            s['dielectric'] = 'tantalum'
        elif re.search(r'\b(POLYMER|SP-CAP|OS-CON|CAP PL\b|C-POLY)', u):
            s['dielectric'] = 'polymer'
        elif re.search(r'\b(E/C|EC CAP|CAP EL|C-AL|C\.EL|ELECTROLYTIC|ELEC\.? ?CAP|ALUMINUM)', u):
            s['dielectric'] = 'electrolytic'
        case = re.search(r'(?<!\d)(3216|3528|6032|7343)(?:/([A-E]))?(?!\d)', u)
        if case and s.get('dielectric') in ('tantalum', 'polymer', None) and re.search(r'TAN|TANT|POLY|CAP PL|CHIP CAP', u):
            package = case.group(1) + (f' ({case.group(2)} case)' if case.group(2) else '')
        dims = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*[*X×]\s*(\d+(?:\.\d+)?)(?:\s*[*X×]\s*\d+(?:\.\d+)?)?(?![\d.])', u)
        if dims and not package and s.get('dielectric') in ('electrolytic', 'polymer'):
            mount = 'Radial ' if re.search(r'\bDIP\b|DIP-T', u) else 'SMD ' if re.search(r'\bSMD\b|\bCHIP\b|C-AL,SMD', u) else ''
            package = mount + re.sub(r'\s*[*X×]\s*', 'x', dims.group(0)) + ' mm'
    elif kind == 'inductor':
        s['inductance_uh'] = _henries_uh(u)
        s['current_a'] = _current(u)
        s['tolerance'] = _tolerance(u)
        m = re.search(r'±\s*(\d*\.?\d+)\s*NH\b', u)
        if m and not s['tolerance']:
            s['tolerance'] = f'±{_num(m.group(1)):g}nH'
    elif kind == 'cm_choke':
        m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*OHM', u)
        s['impedance_ohm'] = _num(m.group(1)) if m else None
        s['frequency_mhz'] = _hertz_mhz(u)
        s['current_a'] = _current(u)
    elif kind == 'ferrite':
        m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*OHM', u)
        s['impedance_ohm'] = _num(m.group(1)) if m else None
        s['frequency_mhz'] = _hertz_mhz(u)
        s['current_a'] = _current(u)
    elif kind == 'thermistor':
        s['resistance_ohm'] = _ohms(u, raw) or _bare_ohms(re.sub(r'^\S+', '', u))
        m = re.search(r'\bB\s*(?:\(25/\d+\))?\s*[=:]?\s*(\d{4})\s*K?\b', u)
        s['b_value_k'] = int(m.group(1)) if m else None
        m = re.search(r'(?<![\d.(])(\d+(?:\.\d+)?)\s*%', u)
        s['tolerance'] = f'{float(m.group(1)):g}%' if m else None
    elif kind == 'crystal':
        s['frequency_mhz'] = _hertz_mhz(u)
        m = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*PF', u)
        s['load_pf'] = _num(m.group(1)) if m else None
        m = re.search(r'(?<![\d.])(\d+)\s*PPM', u)
        s['tolerance_ppm'] = int(m.group(1)) if m else None
        package = None
        m = re.search(r'\b(49US|49/US|HC-?49/?U?S?|UM-1|SMD\s*\d+(?:\.\d+)?[*X]\d+(?:\.\d+)?)\b', u)
        if m:
            package = m.group(1).replace(' ', '')
    elif kind == 'fuse':
        s['current_a'] = _current(u)
        s['voltage_v'] = _voltage(u)
    elif kind == 'varistor':
        s['voltage_v'] = _voltage(u)
    specs = {k: v for k, v in s.items() if v is not None}
    return kind, specs, package


def ic_package(text):
    """Package named on a semiconductor BOM line ('LIN REG. LTC660CS8#TR S-8 LINEAR' -> 'SO-8')."""
    u = clean_bom_text(text).upper()
    m = IC_PACKAGE.search(u)
    if not m:
        return None
    p = m.group(1)
    p = re.sub(r'^S-(\d)', r'SO-\1', p)                      # Asus shorthand S-8 = SO-8
    p = re.sub(r'^S-TO', 'TO-', p)
    p = re.sub(r'^([A-Z]+)(\d)', r'\1-\2', p) if not re.match(r'^(D2?PAK|SM[ABC]|MELF)$', p) else p
    return p


# ---- part numbers -> specs ---------------------------------------------------------
def _code3(code):
    """EIA three-digit code: '472' -> 4700, '229' -> 2.2 (8 and 9 multiply by 0.01 and 0.1)."""
    if not re.fullmatch(r'\d{3}', code):
        return None
    exp = {'8': -2, '9': -1}.get(code[2], int(code[2]))
    return round(int(code[:2]) * 10.0 ** exp, 6)


def _res_code(code):
    """Resistor value codes: '1003' (4-digit E96) -> 100k, '103' -> 10k, '4R7' -> 4.7, '49R9' -> 49.9, '000' -> 0."""
    if 'R' in code:
        a, _, b = code.partition('R')
        return float(f'{a or 0}.{b or 0}')
    if re.fullmatch(r'\d{4}', code):
        return int(code[:3]) * 10 ** int(code[3])
    if re.fullmatch(r'\d{3}', code):
        return _code3(code)
    return None


def _cap_code_pf(code):
    """'150' -> 15pF, '104' -> 100nF, '2R7' -> 2.7pF, 'R90' -> 0.9pF."""
    if 'R' in code:
        a, _, b = code.partition('R')
        return float(f'{a or 0}.{b or 0}')
    v = _code3(code)
    return float(v) if v is not None else None


def _yageo_value(text):
    """'20K', '4K7', '576R', '49R9', '1M', '0R' -> ohms."""
    m = re.fullmatch(r'(\d*)([RKM])(\d*)', text)
    if not m or not (m.group(1) or m.group(3)):
        return None
    return float(f'{m.group(1) or 0}.{m.group(3) or 0}') * {'R': 1, 'K': 1e3, 'M': 1e6}[m.group(2)]


# YAGEO RC_L thick film chip resistors: rated power by size (datasheet)
YAGEO_RC_POWER = {'0201': 0.05, '0402': 0.0625, '0603': 0.1, '0805': 0.125, '1206': 0.25, '1210': 0.5,
                  '2010': 0.75, '2512': 1.0}
RES_SIZE_2 = {'01': '0201', '02': '0402', '03': '0603', '04': '0402', '06': '0603', '08': '0805', '10': '0805',
              '12': '1206', '18': '1210', '20': '2010', '25': '2512'}
RES_TOL = {'B': '0.1%', 'C': '0.25%', 'D': '0.5%', 'F': '1%', 'G': '2%', 'J': '5%'}
MLCC_TOL = {'A': None, 'B': '±0.1pF', 'C': '±0.25pF', 'D': '±0.5pF', 'F': '1%', 'G': '2%', 'J': '5%', 'K': '10%',
            'M': '20%', 'Z': '+80/-20%'}
GRM_SIZE = {'03': '0201', '15': '0402', '18': '0603', '21': '0805', '31': '1206', '32': '1210', '43': '1812'}
GRM_DIEL = {'5C': 'C0G', 'R7': 'X7R', 'R6': 'X5R', 'F5': 'Y5V', 'C8': 'X6S', 'C7': 'X7S', 'D7': 'X7T',
            '1X': 'SL', '2C': 'CH'}
JIS_VOLT = {'0E': 2.5, '0G': 4, '0J': 6.3, '1A': 10, '1C': 16, '1E': 25, '1V': 35, '1H': 50, '2A': 100,
            '2D': 200, '2E': 250, '2J': 630}
CL_SIZE = {'03': '0201', '05': '0402', '10': '0603', '21': '0805', '31': '1206', '32': '1210', '43': '1812'}
CL_DIEL = {'C': 'C0G', 'B': 'X7R', 'A': 'X5R', 'F': 'Y5V', 'X': 'X6S', 'Y': 'X7S'}
CL_VOLT = {'R': 4, 'Q': 6.3, 'P': 10, 'O': 16, 'A': 25, 'L': 35, 'B': 50, 'C': 100, 'D': 200, 'E': 250}
TDK_SIZE = {'0603': '0201', '1005': '0402', '1608': '0603', '2012': '0805', '3216': '1206', '3225': '1210'}
TDK_DIEL = {'C0G': 'C0G', 'COG': 'C0G', 'X7R': 'X7R', 'X5R': 'X5R', 'Y5V': 'Y5V', 'X6S': 'X6S', 'X7S': 'X7S', 'CH': 'CH',
            'JB': None}
YAGEO_CC_SIZE = ('0201', '0402', '0603', '0805', '1206', '1210', '1812')
YAGEO_CC_DIEL = {'NPO': 'C0G', 'X7R': 'X7R', 'X5R': 'X5R', 'Y5V': 'Y5V'}
YAGEO_CC_VOLT = {'4': 4, '5': 6.3, '6': 10, '7': 16, '8': 25, '9': 50, '0': 100, 'A': 200, 'B': 500}
WALSIN_DIEL = {'N': 'C0G', 'B': 'X7R', 'X': 'X5R', 'F': 'Y5V'}
TAIYO_VOLT = {'A': 4, 'J': 6.3, 'L': 10, 'E': 16, 'T': 25, 'G': 35, 'U': 50, 'H': 100}
TAIYO_SIZE = {'063': '0201', '105': '0402', '107': '0603', '212': '0805', '316': '1206', '325': '1210'}
TAIYO_DIEL = {'CH': 'CH', 'CG': 'C0G', 'BJ': None, 'B7': 'X7R', 'C6': 'X6S', 'C7': 'X7S', 'F': 'Y5V'}
DARFON_SIZE = TDK_SIZE
PANA_ECJ_SIZE = {'0': '0402', '1': '0603', '2': '0805', '3': '1206', '4': '1210'}
PANA_ECJ_DIEL = {'B': None, 'C': 'C0G', 'F': 'Y5V', 'R': 'X7R'}
PANA_ERJ_SIZE = {'1G': '0201', '2G': '0402', '2R': '0402', '2B': '0402', '3G': '0603', '3E': '0603', '3R': '0603',
                 '3B': '0603', '6G': '0805', '6E': '0805', '6R': '0805', '6B': '0805', '8G': '1206', '8E': '1206',
                 '8R': '1206', '14': '1210', '12': '1812', '1T': '2512'}


def decode_mpn(manufacturer, part_number):
    """(kind, specs, package) for part numbers whose maker's scheme fixes the ratings, else None.
    Only the fields the number really encodes are returned."""
    mfr = (manufacturer or '').upper()
    pn = re.sub(r'\s+', '', (part_number or '').upper())
    m = None
    # --- resistors ---
    if 'YAGEO' in mfr and (m := re.fullmatch(r'(RC|RT|AC)(\d{4})-?([BCDFGJ])[RKX]-?(?:07|10|13|7D|7W)-?(\d*[RKM]\d*)L?', pn)):
        v = _yageo_value(m.group(4))
        if v is not None and m.group(2) in IMPERIAL:
            spec = {'resistance_ohm': v, 'tolerance': RES_TOL[m.group(3)]}
            if m.group(1) == 'RC' and m.group(2) in YAGEO_RC_POWER:
                spec['power_w'] = YAGEO_RC_POWER[m.group(2)]
            return 'resistor', spec, m.group(2)
    if 'YAGEO' in mfr and (m := re.fullmatch(r'YC(\d)(\d)(\d)-?([FJ])R-?07(\d*[RKM]\d*)L?', pn)):
        v = _yageo_value(m.group(5))
        if v is not None:
            return 'res_array', {'resistance_ohm': v, 'tolerance': RES_TOL[m.group(4)]}, None
    if mfr == 'TA-I' and (m := re.fullmatch(r'RM(\d{2})([BCDFJ])TN(\d*R\d+|\d{3,4})', pn)):
        v = _res_code(m.group(3))
        size = {'02': '0201', '04': '0402', '06': '0603', '10': '0805', '12': '1206', '20': '2010', '25': '2512'}.get(m.group(1))
        if v is not None and size:
            return 'resistor', {'resistance_ohm': float(v), 'tolerance': RES_TOL[m.group(2)]}, size
    if mfr == 'RALEC' and (m := re.fullmatch(r'RTT(\d{2})-?(?:\d{2}T)?(\d*R\d+|\d{3,4})([BDFJ])T[PHE]', pn)):
        v = _res_code(m.group(2))
        size = {'01': '0201', '02': '0402', '03': '0603', '05': '0805', '06': '1206'}.get(m.group(1))
        digits_ok = 'R' in m.group(2) or (len(m.group(2)) == 3) == (m.group(3) == 'J')
        if v is not None and size and digits_ok:
            return 'resistor', {'resistance_ohm': float(v), 'tolerance': RES_TOL[m.group(3)]}, size
    if 'WALSIN' in mfr and (m := re.fullmatch(r'WR(\d{2})X(\d*R\d+|\d{3,4}|000)([BDFJP])TL', pn)):
        v = 0.0 if m.group(3) == 'P' else _res_code(m.group(2))
        size = {'02': '0201', '04': '0402', '06': '0603', '08': '0805', '12': '1206'}.get(m.group(1))
        if v is not None and size:
            spec = {'resistance_ohm': float(v)}
            if m.group(3) != 'P':
                spec['tolerance'] = RES_TOL[m.group(3)]
            return 'resistor', spec, size
    if mfr == 'UNI-OHM' and (m := re.fullmatch(r'(0201|0402|0603|0805|1206)W[A-Z]([BDFJ])(\d*R\d+|\d{4}|\d{3}[JK]?)T[A-Z0-9]{2}', pn)):
        code = m.group(3)
        v = (int(code[:3]) * {'J': 0.1, 'K': 0.01}[code[3]]) if code[-1] in 'JK' else _res_code(code)
        if v is not None:
            return 'resistor', {'resistance_ohm': float(v), 'tolerance': RES_TOL[m.group(2)]}, m.group(1)
    if 'PANASONIC' in mfr and (m := re.fullmatch(r'ERJ-?(\d\d|\d[A-Z])([A-Z]*?)(\d*R\d+|\d{3,4})[A-Z]?', pn)):
        size = '2010' if m.group(1) == '12' and m.group(2).startswith('Z') else PANA_ERJ_SIZE.get(m.group(1))
        v = _res_code(m.group(3))
        letters = m.group(2)
        if size and v is not None:
            spec = {'resistance_ohm': float(v)}
            if v and letters and letters[-1] in RES_TOL:          # the letter before the value: ERJ-3GEY*J*102
                spec['tolerance'] = RES_TOL[letters[-1]]
            return 'resistor', spec, size
    if 'KOA' in mfr and (m := re.fullmatch(r'RK73[HB](1E|1J|2A|2B|2E|3A)T[TD]?[A-Z]{0,2}(\d*R\d+|\d{3,4})([DFGJ])', pn)):
        size = {'1E': '0402', '1J': '0603', '2A': '0805', '2B': '1206', '2E': '1210', '3A': '2512'}[m.group(1)]
        v = _res_code(m.group(2))
        if v is not None:
            return 'resistor', {'resistance_ohm': float(v), 'tolerance': RES_TOL[m.group(3)]}, size
    # --- MLCC ---
    if 'MURATA' in mfr and (m := re.fullmatch(r'GR[MJ](\d{2})\w(\w\w)(\w\w)(\d{3}|\d?R\d+)([A-Z])[\w+#-]*', pn)):
        size, diel, volt = GRM_SIZE.get(m.group(1)), GRM_DIEL.get(m.group(2)), JIS_VOLT.get(m.group(3))
        pf = _cap_code_pf(m.group(4))
        if size and volt and pf is not None:
            spec = {'capacitance_pf': pf, 'voltage_v': volt, 'tolerance': MLCC_TOL.get(m.group(5)), 'dielectric': diel}
            return 'capacitor', {k: v for k, v in spec.items() if v is not None}, size
    if 'SAMSUNG' in mfr and (m := re.fullmatch(r'CL(\d{2})([A-Z])(\d{3}|\d?R\d+)([A-Z])([A-Z])[\w+#-]+', pn)):
        size, diel, volt = CL_SIZE.get(m.group(1)), CL_DIEL.get(m.group(2)), CL_VOLT.get(m.group(5))
        pf = _cap_code_pf(m.group(3))
        if size and volt and pf is not None:
            spec = {'capacitance_pf': pf, 'voltage_v': volt, 'tolerance': MLCC_TOL.get(m.group(4)), 'dielectric': diel}
            return 'capacitor', {k: v for k, v in spec.items() if v is not None}, size
    if mfr == 'TDK' and (m := re.fullmatch(r'C(\d{4})(C0G|COG|X7R|X5R|Y5V|X6S|X7S|CH|JB)(\d[A-Z])(\d{3}|\d?R\d+)([A-Z])[\w+#-]*', pn)):
        size, volt = TDK_SIZE.get(m.group(1)), JIS_VOLT.get(m.group(3))
        pf = _cap_code_pf(m.group(4))
        if size and volt and pf is not None:
            spec = {'capacitance_pf': pf, 'voltage_v': volt, 'tolerance': MLCC_TOL.get(m.group(5)),
                    'dielectric': TDK_DIEL[m.group(2)]}
            return 'capacitor', {k: v for k, v in spec.items() if v is not None}, size
    if 'YAGEO' in mfr and (m := re.fullmatch(r'CC(\d{4})([BCDFGJKMZ])R(NPO|X7R|X5R|Y5V)([0-9AB])B[BN](\d{3}|\d?R\d+)', pn)):
        if m.group(1) in YAGEO_CC_SIZE:
            pf = _cap_code_pf(m.group(5))
            spec = {'capacitance_pf': pf, 'voltage_v': YAGEO_CC_VOLT[m.group(4)], 'tolerance': MLCC_TOL[m.group(2)],
                    'dielectric': YAGEO_CC_DIEL[m.group(3)]}
            return 'capacitor', {k: v for k, v in spec.items() if v is not None}, m.group(1)
    if 'WALSIN' in mfr and (m := re.fullmatch(r'(0201|0402|0603|0805|1206|1210)([NBXF])(\d{3}|\d?R\d+)([BCDFGJKMZ])(\d{3}|\dR\d)[A-Z]?T', pn)):
        pf = _cap_code_pf(m.group(3))
        vc = m.group(5)
        volt = float(vc.replace('R', '.')) if 'R' in vc else int(vc[:2]) * 10 ** int(vc[2])
        spec = {'capacitance_pf': pf, 'voltage_v': volt, 'tolerance': MLCC_TOL[m.group(4)],
                'dielectric': WALSIN_DIEL[m.group(2)]}
        return 'capacitor', {k: v for k, v in spec.items() if v is not None}, m.group(1)
    if 'DARFON' in mfr and (m := re.fullmatch(r'C(\d{4})(NP0|X7R|X5R|Y5V)(\d{3}|\d?R\d+)([BCDFGJKMZ])\w{2,3}', pn)):
        size = DARFON_SIZE.get(m.group(1))
        if size:
            spec = {'capacitance_pf': _cap_code_pf(m.group(3)), 'tolerance': MLCC_TOL[m.group(4)],
                    'dielectric': DIELECTRICS[m.group(2)]}
            return 'capacitor', {k: v for k, v in spec.items() if v is not None}, size
    if 'TAIYO' in mfr and (m := re.fullmatch(r'([AJLETGUH])MK(063|105|107|212|316|325)(CH|CG|BJ|B7|C6|C7|F)(\d{3}|\d?R\d+)([BCDFGJKMZ])[\w+#-]*', pn)):
        spec = {'capacitance_pf': _cap_code_pf(m.group(4)), 'voltage_v': TAIYO_VOLT[m.group(1)],
                'tolerance': MLCC_TOL[m.group(5)], 'dielectric': TAIYO_DIEL[m.group(3)]}
        return 'capacitor', {k: v for k, v in spec.items() if v is not None}, TAIYO_SIZE[m.group(2)]
    if 'PANASONIC' in mfr and (m := re.fullmatch(r'ECJ-?([0-4])([VEYGHU])([BCFR])(\d[A-Z])(\d{3}|\d?R\d+)([BCDFGJKMZ])\w*', pn)):
        volt = JIS_VOLT.get(m.group(4))
        if volt:
            spec = {'capacitance_pf': _cap_code_pf(m.group(5)), 'voltage_v': volt, 'tolerance': MLCC_TOL[m.group(6)],
                    'dielectric': PANA_ECJ_DIEL[m.group(3)]}
            return 'capacitor', {k: v for k, v in spec.items() if v is not None}, PANA_ECJ_SIZE[m.group(1)]
    return None


# makers whose part-number prefix is unique to them: lets a description that is just a
# part number ('ERJ1GEJ102C' on a Samsung service code) be decoded
PREFIX_MAKER = [(r'ERJ|ECJ', 'Panasonic'), (r'GR[MJ]\d', 'Murata'), (r'CL\d\d[A-Z]\d', 'Samsung'),
                (r'(RC|CC|YC|AC)\d{3}', 'YAGEO'), (r'RM\d\d[BCDFJ]TN', 'TA-I'), (r'WR\d\dX', 'Walsin'),
                (r'C\d{4}(C0G|COG|X7R|X5R|Y5V|X6S|X7S|CH|JB)', 'TDK'), (r'(CE)?[AJLETGUH]MK\d{3}', 'TAIYO YUDEN'),
                (r'RTT\d\d', 'RALEC'), (r'RK73', 'KOA')]


def guess_maker(part_number):
    pn = (part_number or '').upper()
    for pattern, maker in PREFIX_MAKER:
        if re.match(pattern, pn):
            return maker
    return None


# ---- combine -----------------------------------------------------------------------
VALUE_KEYS = ('resistance_ohm', 'capacitance_pf', 'inductance_uh', 'impedance_ohm', 'frequency_mhz')


def _close(a, b, rel=0.01):
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-12)


def conflicts(a, b):
    """Keys where two spec dicts disagree (numbers within 1%, strings exactly)."""
    out = []
    for k in set(a) & set(b):
        x, y = a[k], b[k]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            if not _close(float(x), float(y)):
                out.append(k)
        elif str(x) != str(y):
            out.append(k)
    return out


def derive(manufacturer, part_number, description, component_type=''):
    """Best ratings for a component: {'kind', 'specs', 'package', 'source', 'conflict'}.
    Part-number specs win; description specs fill what the number doesn't encode, and are
    dropped altogether when they contradict the number's value (the description then
    belongs to another part - e.g. a BOM line copied onto its alternate)."""
    dk, ds, dp = parse_description(description, component_type)
    mp = decode_mpn(manufacturer, part_number)
    token = clean_bom_text(description).strip()
    if not mp and not ds and re.fullmatch(r'[A-Z0-9-]{8,24}', token or '') and guess_maker(token):
        mp = decode_mpn(guess_maker(token), token)          # the description is another maker's part number
    if not mp:
        return {'kind': dk, 'specs': ds, 'package': dp, 'source': 'description' if ds else None, 'conflict': []}
    mk, ms, mpk = mp
    bad = conflicts(ds, ms) if dk and SITE_TYPE.get(dk) == SITE_TYPE.get(mk) else []
    if dp and mpk and dp != mpk:
        bad.append('package')
    if any(k in VALUE_KEYS for k in bad):
        # the text and the number name different values: one of them is wrong (a line copied
        # from another part, or a typo in the number - RC0603FR-07735R7L on a 35.7 ohm line)
        return {'kind': mk, 'specs': {}, 'package': None, 'source': None, 'conflict': bad}
    if 'package' in bad:
        return {'kind': mk, 'specs': ms, 'package': mpk, 'source': 'part number', 'conflict': bad}
    specs = {**{k: v for k, v in ds.items() if k not in bad}, **ms} if dk and SITE_TYPE.get(dk) == SITE_TYPE.get(mk) else ms
    return {'kind': mk, 'specs': specs, 'package': mpk or dp,
            'source': 'part number + description' if ds else 'part number', 'conflict': bad}
