"""
Parts lists in service manuals.

A service manual's electrical parts list is a table: each row gives a position (reference
designator), the maker's own part code, and a description with the values. Read from
pdftotext -layout (about a second for a 300-page manual), three row shapes are recognised:

    code first        2007-012416   R4509,R4510   R-CHIP;10Kohm,5%,1/16W,TP,1005     (Samsung)
    position first    C518   1-126-960-11   ELECT 1uF 20% 50V                        (Sony, Sharp,
                      R195   HL006150   R.MTL.OXD 1.5KΩ 1/2W  [two tables side by side]   Yamaha...)
    code, then refs   SE000015500   S CER CAP 47U 6.3V M X5R 0603   CH45 CT334 CT335  (factory BOMs)

A page counts only with >= 8 rows, a document only with >= 20 rows of which >= 70% share one
part-code shape (digit/letter pattern): a real parts list has that, scattered schematic labels
don't. The table logic comes from the letus.repair service-manual lane, which read the Samsung,
Sony, Sharp and Yamaha parts the site already has; descriptions are read into ratings with the
same parsers as BOM lines and schematic labels.
"""
import collections
import re
import subprocess
import tempfile

REFDES = (r'(?:IC|Q|D|R|C|L|T|X|F|CN|J|U|VR|SW|BD|FB|TR|ZD|LED|RL|PC|VD|TH|RT|SP|MIC|ANT|BAT|M|K|P|S|Y|E|B|W|H|'
          r'CT|CH|CV|PR|PL|PQ|PU|PD|PJ|RV|LV|UV|CB|JK|ST|RB|RN|RA|RP|RJ|LB|JS|FL|ET|CP|LUG|SC(?=\d{3}))\d{1,5}[A-Z]?')
REFDES_RE = re.compile(rf'^{REFDES}$')
REFLIST_RE = re.compile(rf'^{REFDES}(?:\s*,\s*{REFDES})*,?$')
# Sharp's own codes: 'RH-EXA741WJQZY', 'QSOCNA229WJZZ' (three digits), 'RCiLFA134WJZZY' (a lowercase i), and
# fixed-width (13-14) semiconductor / passive codes padded with / or + ('VSUM6K1N///-1', 'VHiNJM2584M-1Y',
# 'VHD1SS390++-1Y', 'VCFYFA1HA334J+', 'VRS-TP2BD3R3J', 'RCiLP0343TAZZY', 'RR-HRSM1R5J3W')
SHARP = (r'[A-Z]{2,4}-?[A-Zi]{1,4}\d{3,4}WJ[0-9A-Z]{1,4}'
         r'|(?=.{13,14}$)(?:V[CHRS](?=(?:\D*\d){2})[0-9A-Za-z\-/+]{10,11}[0-9A-Z+]|R[A-Z][-i](?=(?:\D*\d){3})[0-9A-Z]{9,10}[0-9A-Z])')
# >= 4 digits: not pin or net names; not a package ('SM0603', 'SOT-363')
CODE_RE = re.compile(r'^(?!(?:SMD?)?(?:01005|0201|0402|0603|0805|1206|1210|2512)$|(?:SOT|SOD|SOP|SOIC|TSSOP|QFN|DFN)-?\d+$)'
                     rf'(?:(?=(?:\D*\d){{4}})[0-9A-Z][0-9A-Z\-./]{{4,24}}|{SHARP})$')
WORDS_RE = re.compile(r'[A-Za-z]{3,}')
VALUE_RE = re.compile(r'\d(?:\.\d+)?\s*(?:UF|NF|PF|UH|NH|K|M|OHM|Ω|V)\b', re.I)
# a maker part number printed beside the internal code on factory BOMs ('MURATA GRM188R60J476ME15D')
MAKER_PN_RE = re.compile(r'\b([A-Z][A-Z0-9]{2,}[0-9][A-Z0-9\-]{3,})\b')

# what a description or a position says the part is (from the letus.repair service-manual lane)
TYPE_WORDS = [
    ('rf_module', r'RF-?MODULE|FRONT-?END MODULE|\bFEM\b|\bPAM\b'), ('balun', r'FILTER|SAW\b|DUPLEXER|DIPLEXER|BALUN'),
    ('mosfet', r'MOSFET|\bFET\b'), ('transistor', r'TRANSISTOR|\bTR\b|\bTRS?\b'),
    # 'DIO SW 200mA 75V' and 'SWITCHING 1N4148W 0.15A' are switching diodes, not switches
    ('diode', r'DIODE|ZENER|SCHOTTKY|RECTIFIER|\bTVS\b|\bDIO\b|^SWITCHING\s+(?:1N\d|BA[SVW]|1SS|MMBD)'), ('led', r'\bLED\b'),
    ('regulator', r'REGULATOR|\bLDO\b|DC-DC|PMIC'), ('crystal', r'CRYSTAL|XTAL|OSCILLATOR|RESONATOR|VIBRATOR'),
    ('capacitor', r'\bCAP|CERAMIC|ELECTROLYTIC|\bELECT\b|TANTALUM|C-CER|MLCC|\bC\.(?:CE|MYLAR|EL|TA)|MYLAR'),
    ('resistor', r'\bRES|R-CHIP|RESISTOR|THICK FILM|\bRST\b|METAL CHIP|METAL GLAZE|CARBON|\bR\.(?:CHP|CAR|MTL)|SHORT CHIP'),
    ('inductor', r'INDUCTOR|\bCOIL|CHOKE'), ('ferrite', r'FERRITE|BEAD'), ('fuse', r'\bFUSE'),
    ('connector', r'CONNECTOR|\bCONN|HEADER|SOCKET|\bJACK|^PLUG\b'),     # Sharp 'Plug, 13Pin(RA)'
    # an IC that switches ('IC-RF SWITCH', 'IC-ANALOG SWITCH', 'IC,Hall Effect Switch') is an IC; 'SW' after a
    # comma is a spring washer ('SCREW-TAPTITE;BH,...,ZPC(WHT),SW')
    ('ic', r'^IC\s*[-,]'), ('switch', r'SWITCH|(?<![,;])\bSW\b|\bSW\.'),
    ('transformer', r'TRANSFORMER'), ('speaker', r'SPEAKER|BUZZER|RECEIVER-?SPK'),
    ('antenna', r'ANTENNA'), ('battery', r'BATTERY'), ('ic', r'\bIC\b|MICOM|CONTROLLER|DRIVER|PROCESSOR'),
]
REF_TYPES = [('IC', 'ic'), ('U', 'ic'), ('ZD', 'diode'), ('LED', 'led'), ('FB', 'ferrite'), ('BD', 'ferrite'),
             ('CN', 'connector'), ('J', 'connector'), ('SW', 'switch'), ('Q', 'transistor'), ('TR', 'transistor'),
             ('D', 'diode'), ('X', 'crystal'), ('Y', 'crystal'), ('L', 'inductor'), ('T', 'transformer'),
             ('VR', 'resistor'), ('R', 'resistor'), ('C', 'capacitor'), ('F', 'fuse')]


def part_type(desc, refs=()):
    d = desc.upper()
    for kind, pattern in TYPE_WORDS:
        if re.search(pattern, d):
            return kind
    for ref in refs[:1]:                # the description didn't say: the position's letters do
        for prefix, kind in REF_TYPES:
            if re.match(rf'^{prefix}\d', ref):
                return kind
    return ''


MIN_PAGE_ROWS = 8
MIN_ROWS = 20
MIN_SHAPE_SHARE = 0.7
MAX_REPEATED_SHARE = 0.25


def shape(code):
    return re.sub(r'[A-Z]+', 'A', re.sub(r'\d+', '9', code))


# Sharp's own codes are one family in several shapes ('RH-EXA103WJZZY', 'QPLGNA341WJZZY', 'QCNCMA012WJZZ'):
# they count together with whichever shapes lead
# (a code the general rule reads already keeps its own shape: moving those out of the shape count changed
# which shape leads, and rows of other shapes that started like it - 'RBLN-0061TAZZY' - were dropped)
SHARP_CODE = re.compile(rf'^(?!(?=(?:\D*\d){{4}})[0-9A-Z][0-9A-Z\-./]{{4,24}}$)(?:{SHARP})$'
                        r'|^[A-Z]{2,4}-?[A-Zi]{1,4}\d{3,4}WJ[0-9A-Z]{1,4}$')
# ... but every Sharp code is kept with the document's family, whatever its shape ('VS2SA1530AR-1Y', 'RH-EX1026CEZZY')
SHARP_FAMILY = re.compile(rf'^(?:{SHARP})$')


def _shapes(codes):
    """(Counter of code shapes, number of Sharp-family codes left out of it)."""
    sharp = sum(1 for c in codes if SHARP_CODE.match(c))
    return collections.Counter(shape(c) for c in codes if not SHARP_CODE.match(c)), sharp


def _layout_pages(raw):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as fh:
        fh.write(raw)
        fh.flush()
        out = subprocess.run(['pdftotext', '-layout', fh.name, '-'], capture_output=True, timeout=300,
                             check=True).stdout.decode('utf-8', 'replace')
    return out.split('\f')


# TPV (Sharp / Philips TV chassis) prints its codes with a space after the group: '093G 64S526SEM'
TPV_CODE = re.compile(r'(?<![\w-])(\d{3}G) (?=[0-9A-Z]{3,})')
TPV_PN = re.compile(r'^\d{3}G[0-9A-Z]{4,}$')
# Sharp (LC-39LE650, LC-46LE540) prints a space inside the position: 'D 3806 VHDHSU119//-1Y  DIODO HSU119TRF'
SPACED_REF = re.compile(r'(?<!\S)([A-Z]{1,3}) (\d{3,4})(?= +([0-9A-Z][0-9A-Z\-./]{4,24})(?!\S))')


# the safety mark printed before a position ('! C806   RC-M2E473RESC   0.047 RE473C 275V Film')
SAFETY_MARK = re.compile(r'^[!⚠]\s+(?=[A-Z])')


def _join_ref(m):
    joined = m.group(1) + m.group(2)
    if REFDES_RE.match(joined) and CODE_RE.match(m.group(3)) and not REFDES_RE.match(m.group(3)):
        return joined + ' '                 # same width: the columns stay where they were
    return m.group(0)


def parse_page(text):
    """[(code, [refs], description)] for the parts-list rows on one page."""
    rows = []
    # positions printed with a space are joined only on a page with several of them, not one on a pinout
    spaced = sum(1 for m in SPACED_REF.finditer(text) if _join_ref(m) != m.group(0)) >= 3
    for line in text.splitlines():
        line = TPV_CODE.sub(r'\1', line) if 'G ' in line else line
        line = SPACED_REF.sub(_join_ref, line) if spaced else line
        chunks = [c.strip() for c in re.split(r'\s{3,}', line.strip()) if c.strip()]
        if len(chunks) < 2:
            continue
        # factory BOM: code, description, refs at the end ('SE000015500  S CER CAP ...  CH45 CT334')
        tail = chunks[-1].replace(',', ' ').split()
        if (len(chunks) >= 3 and CODE_RE.match(chunks[0]) and tail and all(REFDES_RE.match(t) for t in tail)
                and WORDS_RE.search(chunks[1]) and not REFLIST_RE.match(chunks[1].replace(' ', ''))):
            middle = chunks[1:-1]
            # a quantity column ('EBC61856101  Resistor,Chip  1  R8401' - LG): the count of the positions
            if len(middle) >= 2 and middle[-1].isdigit() and int(middle[-1]) == len(tail):
                middle = middle[:-1]
            rows.append((chunks[0], tail, ' '.join(middle)))
            continue
        # code first: CODE, refdes list, description
        if (len(chunks) >= 3 and CODE_RE.match(chunks[0]) and REFLIST_RE.match(chunks[1].replace(' ', ''))
                and WORDS_RE.search(chunks[2])):
            refs = [r for r in re.split(r'\s*,\s*', chunks[1].replace(' ', '')) if r]
            rows.append((chunks[0], refs, ' '.join(chunks[2:4])))
            continue
        # position first, possibly repeated across the line: REF CODE DESC [REF CODE DESC]; the three
        # may be one space apart ('R195 HL006150 R.MTL.OXD 1.5KΩ 1/2W')
        i = 0
        while i < len(chunks):
            safety = SAFETY_MARK.match(chunks[i])
            chunk = chunks[i][safety.end():] if safety else chunks[i]
            words = chunk.split()
            if len(words) >= 2 and REFDES_RE.match(words[0]) and CODE_RE.match(words[1]) \
                    and not REFDES_RE.match(words[1]):
                ref, code, first, j = words[0], words[1], words[2:], i + 1
            elif REFDES_RE.match(chunk) and i + 1 < len(chunks) and CODE_RE.match(chunks[i + 1].split()[0]) \
                    and not REFDES_RE.match(chunks[i + 1].split()[0]):
                parts = chunks[i + 1].split()
                ref, code, first, j = chunk, parts[0], parts[1:], i + 2
            else:
                i += 1
                continue
            # the description runs on over the next columns until the next position + code
            desc = list(first)
            while j < len(chunks) and not _starts_row(chunks, j):
                desc.append(chunks[j])
                j += 1
            desc = ' '.join(desc)
            if WORDS_RE.search(desc) or VALUE_RE.search(desc):
                rows.append((code, [ref], '⚠ ' + desc if safety else desc))
                i = j
            else:
                i += 1
    return [(code, refs, '⚠ ' + _tidy(code, desc[2:]) if desc.startswith('⚠ ') else _tidy(code, desc))
            for code, refs, desc in rows]


# a table's next section heading read onto the row above it ('C CERAM 0402 100NF 25V 20%  RESISTORS')
SECTION_HEADING = re.compile(r'\s+(?:(?:INTEGRATED|PACKAGED|MISCELLANEOUS|SMD)\s+)?(?:RESISTORS|CAPACITORS|COILS|DIODES|'
                             r'TRANSISTORS|CIRCUITS|CONNECTORS|FILTERS|CRYSTALS|TRANSFORMERS|SWITCHES|VARISTORS|'
                             r'FUSES|INDUCTORS|MISCELLANEOUS|MISCELLANEOUS PARTS)$')
SHARP_PRICE = re.compile(r'\s+[JSPR](?:\s+A[A-Z]){1,2}$|(?:\s+A[A-Z]){2}$')
SHARP_MARK_NO_PRICE = re.compile(r'\s+[JSPR](?:\s+-{2,}){2}\s*$')     # '22 KY 50V Electrolytic  J  --  --'
LETTER_SPACED = re.compile(r'(?<!\S)[A-Z] [A-Z] [A-Z](?![a-z])')     # not 'N J Capacitor'
# 'AD J Capacitor, 10 16V Ceramic', 'AB N J Capacitor 4.7 10V', 'N J Capacitor 0.22 50V', 'J Capacitor, 0.22 50V'
SHARP_PRICE_FIRST = re.compile(r'^(?:N\s+)?A[A-Z]\s+(?:N\s+)?[JSPR]\s+(?=\S)|^N\s+[JSPR]\s+(?=[A-Z][a-z])'
                               r'|^[JSPR]\s+(?=(?:Capacitor|Resistor|Coil|Ferrite|Balun|Lug|Zener|Diode|DIO|TR|FET|IC|JUMP)\b)')


def _tidy(code, desc):
    """A description without the empty '-' / '--' columns, and on TPV codes without the one- or two-letter
    vendor mark printed after the code ('061G0402220 JY  RST CHIPR 22 OHM'), and without Sharp's mark and
    price-rank columns ('0.1 25V Ceramic  J  AA  AA', 'RES 0603 0 OHM 5% 1/10W SMD  P  AA'): the J there
    is a delivery mark, not a tolerance."""
    desc = SHARP_MARK_NO_PRICE.sub('', desc)
    desc = re.sub(r'(?:\s+-+)+\s*$', '', desc).strip()
    desc = SECTION_HEADING.sub('', desc)
    if not LETTER_SPACED.search(desc):     # 'F I LTE R - S AW' (Samsung) is a word, not a price column
        desc = SHARP_PRICE_FIRST.sub('', SHARP_PRICE.sub('', desc))
    if TPV_PN.match(code):
        desc = re.sub(r'^[A-Z]{1,2}\s+(?=\S)', '', desc)
    return desc


def _starts_row(chunks, j):
    safety = SAFETY_MARK.match(chunks[j])
    chunk = chunks[j][safety.end():] if safety else chunks[j]
    words = chunk.split()
    if len(words) >= 2 and REFDES_RE.match(words[0]) and CODE_RE.match(words[1]) and not REFDES_RE.match(words[1]):
        return True
    return bool(REFDES_RE.match(chunk) and j + 1 < len(chunks) and chunks[j + 1].split()
                and CODE_RE.match(chunks[j + 1].split()[0]) and not REFDES_RE.match(chunks[j + 1].split()[0]))


# --- tables whose code column comes later in the row ----------------------------------------------
# Sony VAIO location index:  C50  A  41.7500  32.8500  6E5  2200pF  6.3V  10%  112862811  CAP, CERAMIC...  DNI
# Onkyo:                     T901  P TRANS  NPT-1516D  1  2301798  !  <MDC,MDD,MDF>
# Sony PSP (S/U column):     U  C1064  CERAMIC CHIP  0.1uF  10%  10V     (unsupplied parts carry no code)
CHUNK = re.compile(r'\S+(?:[ ]{1,2}\S+)*')
ROW_START = re.compile(rf'^({REFDES})(?: or)?$')
SUPPLY_MARK = re.compile(r'^[SU]$')
DECIMAL = re.compile(r'^-?\d+\.\d+$')
GRID = re.compile(r'^\d{1,2}[A-Z]\d{1,2}$')
QTY = re.compile(r'^\(?\s*\d{1,3}\s*\)?$')
VALUE_CELL = re.compile(r'^[\d.]+\s*(?:[PNUM]?F|[KMR]|OHMS?|Ω|K?V|W|%|[UNM]H|MHZ|KHZ)$|^\d{1,3}$|^\d+\.\d+$', re.I)
SKIP_CELL = re.compile(r'^(?:[AB]|-+|\*+|!|⚠)$')


def _late_rows(text):
    """Rows that start at a position whose part code comes later: [{ref, sc, cells: [(column, text)], alt}]."""
    rows = []
    for line in text.splitlines():
        cells = [(m.start(), m.group()) for m in CHUNK.finditer(line.replace('\t', '   '))]
        k = 0
        while k < len(cells):
            sc = None
            if SUPPLY_MARK.match(cells[k][1]) and k + 1 < len(cells) and ROW_START.match(cells[k + 1][1]):
                sc, k = cells[k][1], k + 1
            m = ROW_START.match(cells[k][1])
            if not m or (k + 1 < len(cells) and ROW_START.match(cells[k + 1][1])):
                k += 1
                continue
            j = k + 1
            while j < len(cells):
                if ROW_START.match(cells[j][1]) and not (j + 1 < len(cells) and ROW_START.match(cells[j + 1][1])):
                    break
                if SUPPLY_MARK.match(cells[j][1]) and j + 1 < len(cells) and ROW_START.match(cells[j + 1][1]):
                    break
                j += 1
            rows.append({'ref': m.group(1), 'sc': sc, 'cells': cells[k + 1:j], 'alt': cells[k][1].endswith(' or')})
            k = j
    return rows


def _is_code_cell(t):
    return bool(CODE_RE.match(t) and not DECIMAL.match(t) and not GRID.match(t) and not VALUE_CELL.match(t))


def parse_page_late(text):
    """[(code, [ref], description)] for tables with the code further along the row; the code column is
    the one where code-shaped cells line up best (same character column, same shapes) on this page.
    Rows of a supplied/unsupplied (S/U) table may have no code: code ''."""
    rows = _late_rows(text)
    columns = collections.defaultdict(collections.Counter)
    for r in rows:
        for col, t in r['cells']:
            if _is_code_cell(t):
                columns[col // 4][shape(t)] += 1
    def score(bucket):
        c = columns.get(bucket)
        if not c:
            return 0
        n = sum(c.values())
        return n * sum(v for _, v in c.most_common(3)) / n if n >= 5 else 0
    def after_qty(r, cell):                 # Onkyo: ... Q'TY  PART NO. - the code that follows a quantity
        k = r['cells'].index(cell)
        return k > 0 and bool(QTY.match(r['cells'][k - 1][1]))
    out = []
    for r in rows:
        best = max((cell for cell in r['cells'] if _is_code_cell(cell[1])),
                   key=lambda c: (score(c[0] // 4) * (1.5 if after_qty(r, c) else 1)), default=None)
        code = best[1] if best and score(best[0] // 4) else ''
        if not code and not r['sc']:
            continue
        cells = [t for col, t in r['cells'] if (col, t) != best]
        numbers = sum(1 for t in cells if DECIMAL.match(t))
        desc = []
        for t in cells:
            if SKIP_CELL.match(t) or GRID.match(t) or (numbers >= 2 and DECIMAL.match(t)) or (code and QTY.match(t)):
                if t in ('!', '⚠'):
                    desc.append('⚠')
                continue
            if t.upper() in ('DNI', 'NS', 'N.M'):
                desc.append('(not fitted)' if t.upper() != 'NS' else '(not supplied)')
                continue
            if t.startswith('<') and t.endswith('>'):
                desc.append(f'(models {t[1:-1]})')
                continue
            desc.append(t)
        desc = ' '.join(desc)
        if r['alt']:
            desc = f'alternative part: {desc}'
        if WORDS_RE.search(desc) or VALUE_RE.search(desc):
            out.append((code, [r['ref']], desc))
    return out


# LG replacement part lists: No, part code, description, quantity, locations; a long location list
# wraps onto lines of its own, above or below its row ('  37 EAG64672301   C-Clip   9'), and may break
# inside a position ('...,C2344,C2' / '137   ECCH0009101 Capacitor,Ceramic,Chip   47   347,C2349,...')
INDEXED_FIRST = re.compile(r'^\d{1,4} (\S+)$')
INDEXED_FIRST_DESC = re.compile(r'^(\d{1,4} \S+) (.+)$')    # code and description one space apart (K350)
INDEXED_LAST = re.compile(r'^(\d{1,4})(?: (.+))?$')
LOC_TEXT = re.compile(r'^[,\s]*[A-Z0-9]+(?:[,\s]+[A-Z0-9]+)*[,\s]*$')


def _indexed_row(line):
    """(code, description, quantity, locations text) or None."""
    chunks = [c.strip() for c in re.split(r'\s{3,}', line.strip()) if c.strip()]
    if len(chunks) >= 4 and re.fullmatch(r'\d{1,4}', chunks[0]):
        chunks = [f'{chunks[0]} {chunks[1]}'] + chunks[2:]          # 'No' and code a column apart
    if len(chunks) >= 3 and re.fullmatch(r'\d{1,4}', chunks[-2]) and _locs(chunks[-1]):
        chunks = chunks[:-2] + [f'{chunks[-2]} {chunks[-1]}']        # so are quantity and locations
    if len(chunks) == 2 and INDEXED_FIRST_DESC.match(chunks[0]):
        chunks = list(INDEXED_FIRST_DESC.match(chunks[0]).groups()) + chunks[1:]
    if len(chunks) < 3:
        return None
    first, last = INDEXED_FIRST.match(chunks[0]), INDEXED_LAST.match(chunks[-1])
    if not (first and last):
        return None
    return first.group(1), ' '.join(chunks[1:-1]), int(last.group(1)), last.group(2) or ''


def _refs(text):
    refs = [r for r in re.split(r'[\s,]+', text.strip()) if r]
    return refs if refs and all(REFDES_RE.match(r) for r in refs) else None


def _locs(text):
    """Locations text, possibly cut inside a position at either end ('347,C2349,...,C2'), or None."""
    if not LOC_TEXT.match(text):
        return None
    words = [w for w in re.split(r'[\s,]+', text.strip()) if w]
    inner = [w for k, w in enumerate(words) if not (k == 0 and w.isdigit()) and not (k == len(words) - 1 and re.fullmatch(r'[A-Z]{1,4}\d*', w))]
    return text if words and all(REFDES_RE.match(w) for w in inner) and any(REFDES_RE.match(w) for w in words) else None


def _join_locs(a, b):
    if not a:
        return b
    if b[:1].isdigit() and a[-1:].isalnum():                       # a position cut at the line end
        return a + b
    return f'{a},{b}'


def _count(locs):
    return len([w for w in re.split(r'[\s,]+', locs) if w])


def parse_page_indexed(text):
    """[(code, refs, description)] for an indexed table; a row's locations are its own plus wrapped lines,
    until it has as many as its quantity."""
    rows, loose = [], ''                     # loose: wrapped locations not yet given to a row
    for line in text.splitlines():
        m = _indexed_row(line)
        if m and CODE_RE.match(m[0]) and WORDS_RE.search(m[1]):
            locs = m[3] if _locs(m[3]) else ''
            if _count(locs) < m[2] and loose:
                locs = _join_locs(loose, locs) if locs else loose
            loose = ''
            rows.append([m[0], locs, m[1], m[2]])
            continue
        if not _locs(line):
            continue
        if rows and _count(rows[-1][1]) < rows[-1][3]:
            rows[-1][1] = _join_locs(rows[-1][1], line.strip())
        else:
            loose = _join_locs(loose, line.strip())
    out = []
    for code, locs, desc, qty in rows:
        refs = _refs(locs) if locs else None
        if refs and len(refs) <= qty:
            out.append((code, refs, desc))
    return out


def _page_kept(rows):
    """A page is a parts-list page when it has enough rows and its codes keep to a few shapes, or (S/U
    tables) enough rows of the supplied/unsupplied kind."""
    if len(rows) < MIN_PAGE_ROWS:
        return False
    coded = [r for r in rows if r[0]]
    if len(rows) - len(coded) >= MIN_PAGE_ROWS:
        return True
    shapes, sharp = _shapes([r[0] for r in coded])
    return bool(coded) and (sum(v for _, v in shapes.most_common(3)) + sharp) / len(coded) >= MIN_SHAPE_SHARE


def page_rows(text):
    """One page's rows, from whichever layout reads it: code first or position first, code further along,
    or indexed (LG)."""
    rows = parse_page(text)
    for other in (parse_page_late, parse_page_indexed):
        if len(rows) < MIN_PAGE_ROWS:
            more = other(text)
            rows = more if len(more) > len(rows) else rows
    return rows


def parse_document(pages):
    """[(page, code, refs, description)] when the document has a parts list, else ([], why)."""
    kept = []
    for n, text in enumerate(pages, start=1):
        rows = page_rows(text)
        if _page_kept(rows):
            kept += [(n, *r) for r in rows]
    if len(kept) < MIN_ROWS:
        return [], f'{len(kept)} parts-list rows'
    # a marking-code book ('SMD code  Type  Function ... Mnf': B0 AP8821C-10PC, B0 SP809...) reads like one, but
    # its 'positions' are package markings that repeat down the page; a list's positions are each printed once
    # (or twice, for two variants). Share of positions printed 3+ times on their page: code book 31%, lists <= 18%
    per_page = collections.defaultdict(collections.Counter)
    for page, _code, refs, _desc in kept:
        per_page[page].update(refs)
    printed = sum(sum(c.values()) for c in per_page.values())
    repeated = sum(n for c in per_page.values() for n in c.values() if n >= 3)
    if printed and repeated / printed >= MAX_REPEATED_SHARE:
        return [], f'positions repeat on their pages ({repeated} of {printed}): a code table, not a parts list'
    coded = [r for r in kept if r[1]]
    shapes, sharp = _shapes([r[1] for r in coded])
    # a maker's codes come in a few related shapes (Panasonic F1H1H104B047 / ERJ2GEJ103X): the shapes that
    # each hold >= 10% of the rows must together hold >= 70%; then rarer shapes that start like the top
    # one join them (TPV 061G0402220 / 065G040210412KY / 065G0603475A5K)
    family = [sh for sh, c in shapes.most_common(3) if c >= 0.1 * len(coded)]
    if coded and (sum(shapes[sh] for sh in family) + sharp) / len(coded) < MIN_SHAPE_SHARE:
        top, count = shapes.most_common(1)[0] if shapes else ('Sharp', sharp)
        return [], f'part codes inconsistent ({count} of {len(coded)} share {top})'
    start = family[0][:2] if family else ''
    rows = [r for r in kept if not r[1] or shape(r[1]) in family or shape(r[1])[:2] == start or SHARP_FAMILY.match(r[1])]
    family = '/'.join(family + (['Sharp'] if sharp else []))
    return rows, f'{len(rows)} rows, part code shapes {family or "none (S/U table)"}'


# Sharp prints capacitances in uF without the unit, pF with a p: '0.1 25V Ceramic', '47 6.3V Electrolytic', '22p 50V',
# '82 KXG 450V Electrolytic' (a series name before the voltage), '0,047 100V Ceramic', 'Capacitor, 10 16V Ceramic'
BARE_MICROFARADS = re.compile(r'^((?:Capacitor,?\s*)?)(\d+(?:[.,]\d+)?)((?:\s+[A-Z]{1,4}\d*[A-Z]?)?\s*\d+(?:[.,]\d+)?V\s+'
                              r'(?:Ceramic|Electrolytic|Tantalum|Film|Mylar)\b)', re.I)


# ... and with the kind first: 'Ceramic 0.1 25V', 'Electrolytic Cap. 22.00 16.0V', 'Mylar Capacitor 0.0680 50V J',
# 'Ceramic Capacitor-B (chip) 0.0100 50V K', 'Capacitor, 0.22 50V' (the same lists print pF with a p)
BARE_MICROFARADS_AFTER = re.compile(r'^((?:Monolithic\s+)?(?:Ceramic|Electrolytic|Tantalum|Film|Mylar)(?:\s+(?:Capacitor|Cap\.)'
                                    r'(?:-[A-Z])?)?(?:\s+\(chip\))?\s+|Capacitor,?\s+)(\d+(?:[.,]\d+)?)(?=\s+\d+(?:[.,]\d+)?\s*k?V\b)',
                                    re.I)


def _microfarads(m):
    return f'{m.group(1)}{m.group(2).replace(",", ".")}uF{m.group(3)}'


def _microfarads_after(m):
    return f'{m.group(1)}{m.group(2).replace(",", ".")}uF'


# Murata's old series word, then the EIA code, tolerance letter and volts: 'CAPACITOR GRM39F 104Z 25 (1608)SMD'
MURATA_CODED = re.compile(r'\b(GRM\w*)\s+(\d\d)(\d)([BCDFGJKMZ])\s+(\d+(?:\.\d+)?)(?=\s|\(|$)')


def _murata_coded(m):
    return f'{m.group(1)} {int(m.group(2)) * 10 ** int(m.group(3))}PF {m.group(4)} {m.group(5)}V'


# Onkyo names its passives <series>-<value>: chip resistors and ceramics carry an EIA code and a tolerance letter
# ('C-CARBON R RN72K1J-331JE' 330 ohm, 'C-CERA C CK725B1H-103K1' 10 nF 50 V, 'CERA C CK45F50V-223Z'), leaded
# resistors and electrolytics the plain value ('CARBON R R16J-2.2K', 'UTSP C CE04W50V-10M(UTSP)' 10 uF 50 V).
# Checked on the TX-SR507 / HT-R960 lists: the EIA reading gives an E24 value for 1,499 of 1,499 chip resistors
# (the plain one for 430) and for 796 of 820 ceramics (the rest are 4-8 pF, C/D tolerance).
ONKYO_CHIP_R = re.compile(r'\b(RN7\d[A-Z]\d[A-Z])-(\d{2})(\d)([FGJ])\w*')
ONKYO_LEAD_R = re.compile(r'\b(?:R\d{2}J|RNU1(?:/\d)?WCJ|RS\d(?:/\d)?WBJ)-(\d+(?:\.\d+)?)([KM]?)(?=\s|$)')
ONKYO_CERAMIC = re.compile(r'\bC[CK](?:\d{3}[A-Z]{1,2}(\d[A-Z])|45[A-Z]{1,2}(\d+)V)-(\d{2})(\d)([BCDFGJKMZ])\w*')
ONKYO_ELECT = re.compile(r'\b(?:CE04W|CEWX)(\d+(?:\.\d+)?)V[- ](\d+(?:\.\d+)?)M\b')
TOL_PERCENT = {'F': '1%', 'G': '2%', 'J': '5%', 'K': '10%', 'M': '20%', 'Z': '+80/-20%', 'C': '±0.25PF', 'D': '±0.5PF',
               'B': '±0.1PF'}
EIA_VOLTS = {'0J': '6.3', '1A': '10', '1C': '16', '1E': '25', '1V': '35', '1H': '50', '1J': '63', '2A': '100',
             '2E': '250', '2H': '500'}


def _onkyo(clean):
    m = ONKYO_CHIP_R.search(clean)
    if m:
        return f'{clean} {int(m.group(2)) * 10 ** int(m.group(3))} OHM {TOL_PERCENT[m.group(4)]}'
    m = ONKYO_LEAD_R.search(clean)
    if m:
        return f'{clean} {m.group(1)}{m.group(2)} OHM'
    m = ONKYO_CERAMIC.search(clean)
    if m:
        volts = EIA_VOLTS.get(m.group(1)) if m.group(1) else m.group(2)
        return (f'{clean} {int(m.group(3)) * 10 ** int(m.group(4))}PF {TOL_PERCENT[m.group(5)]}'
                + (f' {volts}V' if volts else ''))
    m = ONKYO_ELECT.search(clean)
    if m:
        return f'{clean} {m.group(2)}UF 20% {m.group(1)}V'
    return clean


# zero-ohm links: Sony's 'CONDUCTOR, CHIP (1005)', TPV's 'RST CHIPR MAX0R05 1/16W' (max 0.05 ohm; its code
# 061G0402000 says 000)
ZERO_OHM_LINK = re.compile(r'\bCONDU?CTOR,\s*CHIP\b|\bCHIPR\s+MAX0R0\d\b', re.I)
# inductances in RKM form, u for the point: 'CHIP INDUCTOR 1U8 10% FCI1608F-1R8K' (TPV; 62 of 62 agree with the
# maker part beside them)
RKM_MICROHENRY = re.compile(r'(?<![\w.])(\d+)U(\d+)(?![\w.])')


# resistor arrays as value x elements: 'Resistor Array 68X4 01' (68 ohm x4; its Asus-family code RE044680 says
# 68), 'RES, CHIP NETWORK 56X8 (3816)' - read before, the bare number fallback took the 01 or the 3816 size;
# not a size x elements ('(0603X4)')
ARRAY_VALUE = re.compile(r'(?<![(\w.])(?!(?:01005|0201|0402|0603|0805|1206|1210|2012|1608|1005|3216)X)'
                         r'(\d+(?:\.\d+)?[KM]?)X([2-8])\b', re.I)


def _small_forms(clean):
    if re.search(r'ARRAY|NETWORK|\bRES', clean, re.I):
        clean = ARRAY_VALUE.sub(r'\1 OHM X\2', clean)
    if ZERO_OHM_LINK.search(clean):
        clean += ' 0 OHM'
    if re.search(r'INDUC|COIL|CHOKE', clean, re.I):
        clean = RKM_MICROHENRY.sub(r'\1.\2uH', clean)
    return clean


def clean_description(desc, micro_as_m=False):
    """A parts-list description as the site stores it: one line, the maker's value forms spelled out."""
    clean = re.sub(r'\s+', ' ', desc.replace('⚠', ' ')).strip()
    if micro_as_m:
        clean = re.sub(r'(?<=\d)M([FH])\b', r'u\1', clean)
    clean = BARE_MICROFARADS_AFTER.sub(_microfarads_after, BARE_MICROFARADS.sub(_microfarads, clean))
    return _small_forms(_onkyo(MURATA_CODED.sub(_murata_coded, clean)))


def build_candidates_from_parts_list(file_obj, brand=''):
    """Suggestion rows from a service manual's parts list, or [] when it has none. `brand`: the
    product's maker - a manual's part codes are its maker's own service numbers (Sony 1-126-960-11),
    filed under that maker as the site files them."""
    file_obj.seek(0)
    return candidates_from_pages(_layout_pages(file_obj.read()), brand)


def candidates_from_pages(pages, brand=''):
    """build_candidates_from_parts_list for a manual already read to text, one string per page
    (pdftotext -layout) - also what the Norway import lane runs, so both read a list the same way."""
    from apps.components.spec_parse import decode_mpn, guess_maker, parse_description, SITE_TYPE
    from .schematic_values import designator_kind, generic_name

    rows, _why = parse_document(pages)
    # Sony prints micro as m in its parts lists - its legend: 'uF : mF', 'uH : mH'
    micro_as_m = brand.lower() == 'sony' or any(re.search(r'u\s*F\s*:\s*m\s*F', p) for p in pages)
    candidates = []
    for page, code, refs, desc in rows:
        safety = '⚠' in desc                    # the manual's mark for a safety-critical part
        clean = clean_description(desc, micro_as_m)
        kind = part_type(clean, refs) or designator_kind(refs[0] if refs else '')
        k, specs, package = parse_description(clean, kind or '')
        kind = (SITE_TYPE.get(k, k) if k else None) or kind
        decoded = decode_mpn(brand, code) if brand else None       # the maker's code may carry the value
        if decoded:
            specs = {**decoded[1], **specs}
            package = package or decoded[2]
        # a factory BOM prints the maker part number in the description's columns
        maker, part = brand, code
        if not code:                            # an unsupplied part (S/U table): a Generic part by its values
            maker, part = 'Generic', generic_name(kind, specs, package)
        for token in MAKER_PN_RE.findall(clean.upper()):
            guessed = guess_maker(token)
            if guessed and decode_mpn(guessed, token):
                maker, part = guessed, token
                break
        if not part:
            continue
        candidates.append({
            'page_number': page,
            # the row comes from a table that passed the parts-list checks: its position and code are sure
            'confidence': 'high',
            'reference_designator': ', '.join(refs),
            'part_number': part,
            'manufacturer': maker or '',
            'component_type': kind or '',
            'package_type': package or '',
            'description': (clean + ('; safety-critical part: replace with the same type' if safety else ''))[:500],
            'value_raw': clean[:200],
            'quantity': len(refs) or 1,
            'location_description': '',
            'extraction_context': f'Parts list, page {page}: {code or "(no code)"}  {" ".join(refs)}  {clean[:120]}',
        })
    return candidates


def manual_candidates(file_obj, brand=''):
    """Rows for a manual or service document: its parts list when it has one (fast, exact), else the
    older table/text pass (pdf_bom_utils). Returns (rows, exact) - exact when they came from a parts list."""
    from .pdf_bom_utils import build_candidates_from_pdf
    from .schematic_ocr_utils import group_identical

    candidates = build_candidates_from_parts_list(file_obj, brand)
    if candidates:
        return group_identical(candidates), True        # 'R100, R105' x2: one row per part code
    file_obj.seek(0)
    return build_candidates_from_pdf(file_obj), False


def attach_matches(candidates, exact):
    """Give each row 'matched_component': parts-list codes in one exact query, older rows one by one."""
    from .pdf_bom_utils import find_component_match, match_components_exactly

    if exact:
        match_components_exactly(candidates)
        return candidates
    for candidate in candidates:
        match = find_component_match(candidate['part_number'], candidate['manufacturer'])
        candidate['matched_component'] = {'id': str(match.id), 'part_number': match.part_number,
                                          'manufacturer': match.manufacturer} if match else None
    return candidates


def extract_manual_candidates(file_obj, brand=''):
    return attach_matches(*manual_candidates(file_obj, brand))
