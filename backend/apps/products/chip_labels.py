"""
Reading a chip's part number out of a schematic label.

The schematic extractor keeps a chip's label as its part number and marks the row for
review, because no factory BOM confirmed it. The labels follow house styles that a
distributor search does not know:

    MSI       1N4148S, 2N3904S            an S for "SMD" glued to a JEDEC number
              1N4148-S-LL34, BAT54A-S-SOT23   number, S, package
              NPN-3904LT1-S-SOT23         type word, the number without its MMBT prefix, S, package
    Gigabyte  2N7002-SOT23, TI-LM358-SOIC8    number-package, sometimes a maker word first
    ASUS      1N4148W-F, SI2303DS         the maker's own suffixes (kept: they are part of the number)

candidates(label) gives the part numbers worth asking a distributor for, best first, and
split() the package the label names. standard_from_label(label) recognises industry-
standard numbers (JEDEC 1N/2N, Pro Electron BAxxx/BCxxx/BZXxx, 74-series logic, MMBT SMD
transistors) that any maker's part satisfies: those rows are confirmed without asking
anyone, as a Generic part of the standard number. junk(label) spots what is not a part at
all: a net name the extractor took for a chip (DMICLK100P, 1394CLK) or a bare package
(SOT-223), to be dropped once no distributor knows it either.
"""
import re

PACKAGE = re.compile(
    r'^(?:SOT(?:23|323|223|89|363|563|26|25)(?:-?[3-6])?|SOD(?:123|323|523|80|110|128)[A-Z]{0,2}|LL(?:34|41)|'
    r'SM[ABC]|DO(?:2[14][14][A-Z]{0,2}|41|35|15)|D2?PAK|TO(?:252|263|220|92|251|126)(?:-?\d)?|'
    r'(?:SOIC|SOP|SSOP|TSSOP|MSOP|QFN|DFN|TQFP|LQFP|PLCC|BGA|TSOP|WSON|SON|DIP|PDIP|QSOP|VSSOP|HSOP)\d{0,3}[A-Z]?|SC(?:59|70|88|89)A?)$', re.I)
PACKAGE_DASH = re.compile(r'\b(SOT|SOD|TO|DO|LL|SM|SOIC|SOP|SSOP|TSSOP|MSOP|QFN|DFN|TQFP|LQFP|PLCC|BGA|TSOP|WSON|DIP|PDIP|SC)-(\d)', re.I)
from apps.products.schematic_values import VALUE_WORD as RATING    # '75V', '10uF'; not '83627F'
# words a label puts in front of the number: the kind of part, or the maker
TYPE_WORDS = {'NPN', 'PNP', 'ESD', 'TVS', 'ZENER', 'DIODE', 'MOS', 'MOSFET', 'FET', 'LDO', 'REG', 'PWM', 'IC', 'SW',
              'MOSDVR', 'INTS', 'NN', 'LED', 'XTAL', 'OSC', 'CLK', 'SMD', 'S'}
MAKER_WORDS = {'TI': 'Texas Instruments', 'NS': 'Texas Instruments', 'ON': 'onsemi', 'ST': 'STMicroelectronics',
               'NXP': 'NXP', 'PHILIPS': 'NXP', 'FAIRCHILD': 'onsemi', 'ROHM': 'ROHM', 'VISHAY': 'Vishay',
               'DIODES': 'Diodes Incorporated', 'INFINEON': 'Infineon', 'MAXIM': 'Maxim', 'INTEL': 'Intel',
               'WINBOND': 'Winbond', 'REALTEK': 'Realtek', 'RICHTEK': 'Richtek', 'ANPEC': 'Anpec', 'AOS': 'Alpha & Omega',
               'INTERSIL': 'Intersil', 'ITE': 'ITE', 'ICS': 'IDT', 'NIKO': 'Niko Semiconductor', 'ATL': ''}
JEDEC = re.compile(r'^((?:1N|2N)\d{3,5}[A-RT-Z]?)(?:S|SR|-R|S-R)?$')  # the MSI 'S' (SMD) and reel marks stripped
MMBT = re.compile(r'^MMBT\d{4}[A-Z0-9]{0,5}$')                         # SMD 2N transistors, every maker
# Pro Electron: B + type letter(s) + 2-3 digits + a grade letter or two (BAT54A, BAV99, BC847B,
# BSS138, BZX84C5V1); not a maker's own code with digits after the letters (Infineon BSC032N03S)
PRO_ELECTRON = re.compile(r'^B(?:A[STVWX]|C[A-Z]?|D[A-Z]?|F[A-Z]?|S[A-Z]|Z[XVT])\d{2,3}[A-Z]{0,2}(?:C?\d+V\d+)?$')
JIS = re.compile(r'^2S[ABCDJK]\d{3,4}[A-Z]{0,3}$')                     # JEITA-registered transistors: 2SC1815, 2SB1197K
LOGIC = re.compile(r'^(?:SN|MC|CD|HD|TC|M|NC)?74[A-Z]{1,5}\d{1,4}[A-Z0-9]{0,6}$|^(?:CD|HEF|MC1)4\d{3}[A-Z]{0,4}$')
NET = re.compile(r'^(?:[A-Z]{0,4}\d{0,4}(?:CLK|RST|PWR|PLL|SCLK)\d{0,4}[PN]?|VCC\w*|VDD\w*|GND\w*|VSS\w*)$')
BARE_TRANSISTOR = re.compile(r'^(?:M?MBT)?(\d{4}[A-Z0-9]{0,5})$')      # '3904LT1' behind NPN-/PNP-


def split(label):
    """(core, package, type_words, maker): the label's tokens sorted into the part number's
    own, the package and rating tail, and the type and maker words in front."""
    text = PACKAGE_DASH.sub(r'\1\2', label.strip().upper())
    tokens = [t for t in re.split(r'[-\s/]+', text) if t]
    package, maker, kinds = None, None, []
    while len(tokens) > 1 and (PACKAGE.match(tokens[-1]) or RATING.match(tokens[-1]) or tokens[-1] in ('S', 'SMD')):
        t = tokens.pop()
        if PACKAGE.match(t):
            package = package or t
    if len(tokens) == 1 and PACKAGE.match(tokens[0]):
        package = package or tokens.pop()     # the label is only a package: SOT-223
    while tokens and (tokens[0] in TYPE_WORDS or tokens[0] in MAKER_WORDS):
        t = tokens.pop(0)
        if t in MAKER_WORDS and MAKER_WORDS[t]:
            maker = MAKER_WORDS[t]
        elif t in TYPE_WORDS:
            kinds.append(t)
    return '-'.join(tokens), package, kinds, maker


def candidates(label):
    """Part numbers worth asking for, best first, without duplicates."""
    core, package, kinds, maker = split(label)
    out = []
    if not core:
        return out
    if {'NPN', 'PNP'} & set(kinds) or (package and package.startswith('SOT23') and re.fullmatch(r'\d{4}', core)):
        m = BARE_TRANSISTOR.match(core)
        if m:
            out += [f'MMBT{m.group(1)}', f'2N{m.group(1)[:4]}']     # '3904-S-SOT23' is a transistor, not Heyco's cable tie 3904
    if re.fullmatch(r'\d+', core):
        return out                            # a bare number alone matches anything at a distributor: never ask for it
    j = JEDEC.match(core)
    if j and j.group(1) != core:
        out.append(j.group(1))                # 1N4148S -> 1N4148 before the label itself
    out.append(core)
    if core.endswith('S') and len(core) > 5 and not j:
        out.append(core[:-1])                 # the S for SMD glued on (LT1087S); tried after the label itself
    if '-' in core:
        out.append(core.replace('-', ''))
    seen, unique = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def standard_type(mpn):
    """The standard number a multi-sourced part goes by, or None."""
    u = (mpn or '').upper()
    j = JEDEC.match(u)
    if j:
        return j.group(1)
    if MMBT.match(u) or PRO_ELECTRON.match(u) or LOGIC.match(u) or JIS.match(u):
        return u
    return None


def standard_from_label(label):
    """The standard number a label names once its decorations are gone, or None.
    '1N4148S' -> '1N4148'; 'NPN-3904LT1-S-SOT23' -> 'MMBT3904LT1'; 'LT1087S' -> None."""
    for c in candidates(label):
        s = standard_type(c)
        if s:
            return s
    return None


def line_candidates(name):
    """Part numbers worth asking for in a whole BOM line kept as a part's name ('FLASH MXIC
    MX25L8005PC-15G 8M SPI PDIP-8'): the part-shaped words, longest first, at most three.
    [] when the line has no such word ('ANCHOR CLIP FOR TEHAMA CLIP')."""
    from apps.components.parametric import MAX_EXACT_TRIES, WORD, part_shaped
    words = [w for w in WORD.findall(name or '') if part_shaped(w) and not RATING.match(w) and not PACKAGE.match(w)]
    return sorted(dict.fromkeys(words), key=len, reverse=True)[:MAX_EXACT_TRIES]


def junk(label):
    """Not a part: a net name (DMICLK100P, 1394CLK, VCC33USB4) or a label that is only a
    package or rating (SOT-223). Checked only after no distributor knows the label."""
    core, _, kinds, _ = split(label)
    if kinds:
        return False                          # 'LED-1206': a part with no number, not noise
    return not core or bool(NET.match(core))
