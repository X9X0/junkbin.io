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
          r'CT|CH|CV|PR|PL|PQ|PU|PD|PJ|RV|LV|UV|CB|JK|ST|RB|RN|RA|RP|RJ|LB|JS|FL|ET|CP)\d{1,5}[A-Z]?')
REFDES_RE = re.compile(rf'^{REFDES}$')
REFLIST_RE = re.compile(rf'^{REFDES}(?:\s*,\s*{REFDES})*,?$')
# >= 4 digits: not pin or net names; not a package ('SM0603', 'SOT-363')
CODE_RE = re.compile(r'^(?!(?:SMD?)?(?:01005|0201|0402|0603|0805|1206|1210|2512)$|(?:SOT|SOD|SOP|SOIC|TSSOP|QFN|DFN)-?\d+$)'
                     r'(?=(?:\D*\d){4})[0-9A-Z][0-9A-Z\-./]{4,24}$')
WORDS_RE = re.compile(r'[A-Za-z]{3,}')
VALUE_RE = re.compile(r'\d(?:\.\d+)?\s*(?:UF|NF|PF|UH|NH|K|M|OHM|Ω|V)\b', re.I)
# a maker part number printed beside the internal code on factory BOMs ('MURATA GRM188R60J476ME15D')
MAKER_PN_RE = re.compile(r'\b([A-Z][A-Z0-9]{2,}[0-9][A-Z0-9\-]{3,})\b')

# what a description or a position says the part is (from the letus.repair service-manual lane)
TYPE_WORDS = [
    ('rf_module', r'RF-?MODULE|FRONT-?END MODULE|\bFEM\b|\bPAM\b'), ('balun', r'FILTER|SAW\b|DUPLEXER|DIPLEXER|BALUN'),
    ('mosfet', r'MOSFET|\bFET\b'), ('transistor', r'TRANSISTOR|\bTR\b|\bTRS?\b'),
    ('diode', r'DIODE|ZENER|SCHOTTKY|RECTIFIER|\bTVS\b'), ('led', r'\bLED\b'),
    ('regulator', r'REGULATOR|\bLDO\b|DC-DC|PMIC'), ('crystal', r'CRYSTAL|XTAL|OSCILLATOR|RESONATOR|VIBRATOR'),
    ('capacitor', r'\bCAP|CERAMIC|ELECTROLYTIC|\bELECT\b|TANTALUM|C-CER|MLCC|\bC\.(?:CE|MYLAR|EL|TA)|MYLAR'),
    ('resistor', r'\bRES|R-CHIP|RESISTOR|THICK FILM|\bRST\b|METAL CHIP|METAL GLAZE|CARBON|\bR\.(?:CHP|CAR|MTL)|SHORT CHIP'),
    ('inductor', r'INDUCTOR|\bCOIL|CHOKE'), ('ferrite', r'FERRITE|BEAD'), ('fuse', r'\bFUSE'),
    ('connector', r'CONNECTOR|\bCONN|HEADER|SOCKET|\bJACK'), ('switch', r'SWITCH|\bSW\b|\bSW\.'),
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


def shape(code):
    return re.sub(r'[A-Z]+', 'A', re.sub(r'\d+', '9', code))


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


def parse_page(text):
    """[(code, [refs], description)] for the parts-list rows on one page."""
    rows = []
    for line in text.splitlines():
        line = TPV_CODE.sub(r'\1', line) if 'G ' in line else line
        chunks = [c.strip() for c in re.split(r'\s{3,}', line.strip()) if c.strip()]
        if len(chunks) < 2:
            continue
        # factory BOM: code, description, refs at the end ('SE000015500  S CER CAP ...  CH45 CT334')
        tail = chunks[-1].replace(',', ' ').split()
        if (len(chunks) >= 3 and CODE_RE.match(chunks[0]) and tail and all(REFDES_RE.match(t) for t in tail)
                and WORDS_RE.search(chunks[1]) and not REFLIST_RE.match(chunks[1].replace(' ', ''))):
            rows.append((chunks[0], tail, ' '.join(chunks[1:-1])))
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
            words = chunks[i].split()
            if len(words) >= 2 and REFDES_RE.match(words[0]) and CODE_RE.match(words[1]) \
                    and not REFDES_RE.match(words[1]):
                ref, code, first, j = words[0], words[1], words[2:], i + 1
            elif REFDES_RE.match(chunks[i]) and i + 1 < len(chunks) and CODE_RE.match(chunks[i + 1].split()[0]) \
                    and not REFDES_RE.match(chunks[i + 1].split()[0]):
                parts = chunks[i + 1].split()
                ref, code, first, j = chunks[i], parts[0], parts[1:], i + 2
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
                rows.append((code, [ref], desc))
                i = j
            else:
                i += 1
    return [(code, refs, _tidy(code, desc)) for code, refs, desc in rows]


def _tidy(code, desc):
    """A description without the empty '-' / '--' columns, and on TPV codes without the one- or two-letter
    vendor mark printed after the code ('061G0402220 JY  RST CHIPR 22 OHM')."""
    desc = re.sub(r'(?:\s+-+)+\s*$', '', desc).strip()
    if TPV_PN.match(code):
        desc = re.sub(r'^[A-Z]{1,2}\s+(?=\S)', '', desc)
    return desc


def _starts_row(chunks, j):
    words = chunks[j].split()
    if len(words) >= 2 and REFDES_RE.match(words[0]) and CODE_RE.match(words[1]) and not REFDES_RE.match(words[1]):
        return True
    return bool(REFDES_RE.match(chunks[j]) and j + 1 < len(chunks) and chunks[j + 1].split()
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


def _page_kept(rows):
    """A page is a parts-list page when it has enough rows and its codes keep to a few shapes, or (S/U
    tables) enough rows of the supplied/unsupplied kind."""
    if len(rows) < MIN_PAGE_ROWS:
        return False
    coded = [r for r in rows if r[0]]
    if len(rows) - len(coded) >= MIN_PAGE_ROWS:
        return True
    shapes = collections.Counter(shape(r[0]) for r in coded)
    return bool(coded) and sum(v for _, v in shapes.most_common(3)) / len(coded) >= MIN_SHAPE_SHARE


def parse_document(pages):
    """[(page, code, refs, description)] when the document has a parts list, else ([], why)."""
    kept = []
    for n, text in enumerate(pages, start=1):
        rows = parse_page(text)
        if len(rows) < MIN_PAGE_ROWS:
            late = parse_page_late(text)
            rows = late if len(late) > len(rows) else rows
        if _page_kept(rows):
            kept += [(n, *r) for r in rows]
    if len(kept) < MIN_ROWS:
        return [], f'{len(kept)} parts-list rows'
    coded = [r for r in kept if r[1]]
    shapes = collections.Counter(shape(r[1]) for r in coded)
    # a maker's codes come in a few related shapes (Panasonic F1H1H104B047 / ERJ2GEJ103X): the shapes that
    # each hold >= 10% of the rows must together hold >= 70%; then rarer shapes that start like the top
    # one join them (TPV 061G0402220 / 065G040210412KY / 065G0603475A5K)
    family = [sh for sh, c in shapes.most_common(3) if c >= 0.1 * len(coded)]
    if coded and sum(shapes[sh] for sh in family) / len(coded) < MIN_SHAPE_SHARE:
        top, count = shapes.most_common(1)[0]
        return [], f'part codes inconsistent ({count} of {len(coded)} share {top})'
    start = family[0][:2] if family else ''
    rows = [r for r in kept if not r[1] or shape(r[1]) in family or shape(r[1])[:2] == start]
    family = '/'.join(family)
    return rows, f'{len(rows)} rows, part code shapes {family or "none (S/U table)"}'


def build_candidates_from_parts_list(file_obj, brand=''):
    """Suggestion rows from a service manual's parts list, or [] when it has none. `brand`: the
    product's maker - a manual's part codes are its maker's own service numbers (Sony 1-126-960-11),
    filed under that maker as the site files them."""
    from apps.components.spec_parse import decode_mpn, guess_maker, parse_description, SITE_TYPE
    from .schematic_values import designator_kind, generic_name

    file_obj.seek(0)
    pages = _layout_pages(file_obj.read())
    rows, _why = parse_document(pages)
    # Sony prints micro as m in its parts lists - its legend: 'uF : mF', 'uH : mH'
    micro_as_m = brand.lower() == 'sony' or any(re.search(r'u\s*F\s*:\s*m\s*F', p) for p in pages)
    candidates = []
    for page, code, refs, desc in rows:
        safety = '⚠' in desc                    # the manual's mark for a safety-critical part
        clean = re.sub(r'\s+', ' ', desc.replace('⚠', ' ')).strip()
        if micro_as_m:
            clean = re.sub(r'(?<=\d)M([FH])\b', r'u\1', clean)
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
