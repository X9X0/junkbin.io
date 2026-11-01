"""
Schematic OCR extraction utilities.

Circuit diagrams (full schematics, block diagrams, PCB layouts, wiring
diagrams) don't have textual BOM tables - their components are drawn
symbols with reference-designator labels scattered spatially across the
page, not listed anywhere in reading order. This renders each page to an
image and OCRs it with Tesseract, then looks for designator-shaped tokens
and whatever text sits nearest to them on the page as a rough stand-in
for "the marking printed next to this part."

A PDF exported from a CAD tool (most laptop and phone schematics) already
carries its text: those pages are read straight from the text layer - exact
words and positions, milliseconds per page - and only pages without one
(scans) are rendered and OCR'd.

Confidence is always 'low' here - unlike the text/table pipeline there's
no structural signal (a table header, a reading-order line) confirming a
real pairing, just spatial proximity on a rendered image. This is a
starting point for a human to verify, not a source of truth. Tesseract's
own per-word confidence score is unreliable on schematic line art (a
correctly-read designator can score anywhere from 0 to 90+), so it's
trusted only as a weak secondary filter on the nearby "value" token, not
on the designator match itself - the regex shape match already does that
structural filtering.
"""
import io
import math
import re

from .pdf_bom_utils import REF_DES_PATTERN, classify_component_type


def _engine_version():
    """A fingerprint of the scanning code: cached scan results (SchematicViewSet._scan) are dropped
    by themselves whenever any of it changes."""
    import hashlib
    from pathlib import Path
    here = Path(__file__).parent
    sources = [here / name for name in ('schematic_ocr_utils.py', 'schematic_values.py', 'parts_list_utils.py',
                                        'pdf_bom_utils.py', 'import_text.py')]
    sources.append(here.parent / 'components' / 'spec_parse.py')
    digest = hashlib.sha1()
    for path in sources:
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


SCAN_ENGINE_VERSION = _engine_version()

# Tokens this generic are almost never a useful "marking" next to a part -
# schematic net labels, pin numbers, stray symbols. Skip as candidate values.
NOISE_TOKEN_PATTERN = re.compile(r'^[A-Za-z]{1,2}$|^[0-9]{1,2}$|^[^A-Za-z0-9]+$')

# On text-layer pages the words are exact, so the designator and its value can be held to more:
# designators must use a parts-list prefix (a CPU's BGA ball names - AK57, B58 - and DDR pins
# - DQ12 - are shaped like designators too), and a value is never a net name ('SB_DQ3',
# 'H_PROCHOT#_R'), a rail ('+3VALW'), a page reference ('<17>') or a stuffing-option marker
# ('PX@', 'Z15@').
DESIGNATOR_PREFIX = re.compile(
    r'^(?:R|C|L|U|Q|D|J|Y|X|F|T|K|S|SW|FB|FL|BT|BAT|LED|LD|CN|CON|JP|RN|RP|RA|CP|CR|EC|VR|ZD|IC|MIC|SPK|TR|OSC|'
    r'P[RCLQUDJFHY]|[RCLUQD]V)\d', re.I)
NOT_A_VALUE = re.compile(r'@$|#|,|^[+<]|^[A-Za-z]\+|^[A-Za-z]+\d*_|^[A-Za-z]+\d*/[A-Za-z]|^(?:GND|VCC|VDD|VSS|NC)\b', re.I)
# what a designator's letters say the part is, when its value doesn't ('0.1U_0402_16V7K' is a capacitor)
DESIGNATOR_TYPE = [(r'^(?:LED|LD)', 'led'), (r'^(?:FB|FL)', 'ferrite'), (r'^(?:SW|S)\d', 'switch'),
                   (r'^(?:BT|BAT)', 'battery'), (r'^(?:R|RV|PR|RP|RA|RN|VR)\d', 'resistor'),
                   (r'^(?:C|CV|PC|CP|EC)\d', 'capacitor'), (r'^(?:L|LV|PL)\d', 'inductor'),
                   (r'^(?:D|DV|PD|ZD|CR)\d', 'diode'), (r'^(?:Q|QV|PQ|TR)\d', 'transistor'),
                   (r'^(?:U|UV|PU|IC)\d', 'ic'), (r'^(?:J|CN|CON|JP|PJ)\d', 'connector'),
                   (r'^(?:Y|X|OSC)\d', 'crystal'), (r'^(?:F|PF)\d', 'fuse'), (r'^T\d', 'transformer'),
                   (r'^K\d', 'relay')]


def designator_type(designator):
    return next((t for pattern, t in DESIGNATOR_TYPE if re.match(pattern, designator, re.I)), '')
MAX_PAIR_DISTANCE_PX = 220  # at 300 DPI, roughly within ~0.7in on the rendered page
MIN_VALUE_CONFIDENCE = 30  # tesseract's 0-100 score, applied only to the paired value


def _ocr_image(image):
    """Run Tesseract on a single page image, return word boxes with centers."""
    import pytesseract

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text:
            continue
        try:
            conf = int(float(data['conf'][i]))
        except (TypeError, ValueError):
            conf = -1
        words.append({
            'text': text,
            'conf': conf,
            'x': data['left'][i] + data['width'][i] / 2,
            'y': data['top'][i] + data['height'][i] / 2,
        })
    return words


def _nearest_value(designator_index, words, used_indices, strict=False):
    """Find the closest other word to a designator, ignoring noise/used tokens. strict (exact
    text-layer words): nets, rails and option markers aren't values, and a value has a digit."""
    d = words[designator_index]
    best_index = None
    best_dist = None
    for i, w in enumerate(words):
        if i == designator_index or i in used_indices:
            continue
        if REF_DES_PATTERN.fullmatch(w['text']):
            continue  # don't pair a designator with another designator
        if NOISE_TOKEN_PATTERN.match(w['text']):
            continue
        if w['conf'] < MIN_VALUE_CONFIDENCE:
            continue
        if strict and (NOT_A_VALUE.search(w['text']) or not re.search(r'\d', w['text'])):
            continue
        dist = math.hypot(w['x'] - d['x'], w['y'] - d['y'])
        if dist > MAX_PAIR_DISTANCE_PX:
            continue
        if best_dist is None or dist < best_dist:
            best_index = i
            best_dist = dist
    return best_index


MAX_LABEL_WORDS = 6


def _label_words(i, words, designators):
    """The label printed around designator i on a text-layer page: the words within pairing distance
    that are nearer to it than to any other designator (a label is often several lines - Apple and
    Samsung print '1UF', '10%', '6.3V', 'X5R', '0201' one above the other), nearest first. Nets, rails
    and page references are left out; a build marker ('PX@', '@') is kept for its meaning."""
    d = words[i]
    near = []
    for j, w in enumerate(words):
        t = w['text']
        if j == i or REF_DES_PATTERN.fullmatch(t) or len(t) > 60:
            continue
        marker = t == '@' or re.fullmatch(r'[A-Z0-9]+@', t, re.I)
        if not marker and (NOISE_TOKEN_PATTERN.match(t) or NOT_A_VALUE.search(t) or not re.search(r'\d', t)):
            if not re.fullmatch(r'X5R|X7R|X6S|X7S|C0G|NP0|NPO|Y5V|\d+(?:\.\d+)?%|[FGJKMZ]', t, re.I):
                continue
        dist = math.hypot(w['x'] - d['x'], w['y'] - d['y'])
        if dist > MAX_PAIR_DISTANCE_PX:
            continue
        if any(k != i and math.hypot(w['x'] - words[k]['x'], w['y'] - words[k]['y']) < dist for k in designators):
            continue                    # another part's label
        near.append((dist, t))
    return [t for _, t in sorted(near)[:MAX_LABEL_WORDS]]


BBOX_PAGE = re.compile(r'<page\b.*?</page>', re.S)
BBOX_WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


def _text_layers(raw):
    """Each page's words from the PDF's own text layer (poppler's pdftotext -bbox: the
    PDF's word boundaries, about a second for a 50-page schematic), in _ocr_image's shape,
    positioned as at 300 DPI so the pairing distance means the same."""
    import html
    import subprocess
    import tempfile

    scale = 300 / 72
    with tempfile.NamedTemporaryFile(suffix='.pdf') as fh:
        fh.write(raw)
        fh.flush()
        out = subprocess.run(['pdftotext', '-bbox', fh.name, '-'], capture_output=True, timeout=300,
                             check=True).stdout.decode('utf-8', 'replace')
    pages = []
    for page in BBOX_PAGE.findall(out):
        words = []
        for x0, y0, x1, y1, text in BBOX_WORD.findall(page):
            text = html.unescape(text).strip()
            if text:
                words.append({'text': text, 'conf': 100, 'x': (float(x0) + float(x1)) / 2 * scale,
                              'y': (float(y0) + float(y1)) / 2 * scale})
        pages.append(words)
    return pages


# a page with fewer words than this in its text layer is treated as a scan and OCR'd
MIN_TEXT_LAYER_WORDS = 10


def extract_candidates_from_page(image, page_number, words=None, source='OCR', odm=None):
    """Designator/nearby-value candidates on one page: OCR'd from its rendered image, or
    `words` already read from the PDF's text layer."""
    from .schematic_values import parse_label

    strict = words is not None
    if words is None:
        words = _ocr_image(image)
    candidates = []
    used = set()
    seen_designators = set()
    designators = [k for k, w in enumerate(words)
                   if REF_DES_PATTERN.fullmatch(w['text']) and DESIGNATOR_PREFIX.match(w['text'])] if strict else []

    for i, w in enumerate(words):
        if not REF_DES_PATTERN.fullmatch(w['text']):
            continue
        if w['text'] in seen_designators:
            continue  # same designator OCR'd twice on one page - keep first
        if strict and not DESIGNATOR_PREFIX.match(w['text']):
            continue
        seen_designators.add(w['text'])

        if strict:
            label = _label_words(i, words, designators)
            if not any(re.search(r'\d', t) for t in label):
                continue  # a pin or ball name: real parts on a CAD page have their value printed beside them
        else:
            value_index = _nearest_value(i, words, used, strict)
            label = []
            if value_index is not None:
                used.add(value_index)
                label = [words[value_index]['text']]
        value_text = ' '.join(label)
        parsed = parse_label(label, w['text'], odm) if label else None
        row = _candidate(w['text'], page_number, value_text, parsed, strict, source)
        row['locations'] = [{'ref': w['text'], 'page': page_number, 'x': round(w['x']), 'y': round(w['y'])}]
        row['label_words'] = label
        row['alternatives'] = _alternatives(label, w['text'], odm, row) if strict else []
        candidates.append(row)
    return candidates


def _alternatives(label, designator, odm, row):
    """Other readings of the label for the reviewer to pick from: each word read on its own (a
    neighbour's label caught in the gathering, a second line), different from the row's reading."""
    from .schematic_values import generic_name, parse_label

    out, seen = [], {row['part_number']}
    for word in dict.fromkeys(label):
        p = parse_label([word], designator, odm)
        name = p['part_number'] or generic_name(p['kind'], p['specs'], p['package'])
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({'part_number': name, 'manufacturer': p['maker'] or ('Generic' if not p['part_number'] else ''),
                    'component_type': p['kind'] or '', 'package_type': p['package'] or '', 'source': word})
    return out[:5]


def _candidate(designator, page_number, value_text, parsed, strict, source):
    """One suggestion row from a designator and what its label says. A passive whose label gives its
    value becomes a Generic part named by its ratings ('CAP 100nF 16V X7R 10% 0402'); a printed maker
    part number is kept with its maker when the number tells it. OCR'd labels stay 'low'."""
    from .schematic_values import generic_name

    kind = (parsed or {}).get('kind') or designator_type(designator) or (
        classify_component_type(value_text) if value_text else '')
    name = generic_name(kind, parsed['specs'], parsed['package']) if parsed else None
    part_number, maker = (parsed or {}).get('part_number'), (parsed or {}).get('maker')
    if not part_number and name:
        part_number, maker = name, 'Generic'
    flags = (parsed or {}).get('flags') or []
    reading = name or ''
    description = '; '.join(x for x in (reading, f"schematic label '{value_text}'" if value_text else '', *flags) if x)
    return {
        'page_number': page_number,
        'confidence': (parsed or {}).get('confidence', 'low') if strict else 'low',
        'reference_designator': designator,
        'part_number': part_number or value_text,
        'manufacturer': maker or '',
        'component_type': kind or '',
        'package_type': (parsed or {}).get('package') or '',
        'description': description[:500],
        'value_raw': value_text,
        'quantity': 1,
        'location_description': '',
        'extraction_context': (f"{source}: designator '{designator}' near text '{value_text}'"
                               if value_text else f"{source}: designator '{designator}', no nearby text found"),
    }


def group_identical(candidates):
    """One row per identical part: 'C41, C44, C61' x3 instead of three rows to review."""
    groups, order = {}, []
    for c in candidates:
        flags = tuple(f for f in c['description'].split('; ') if f.startswith(('not fitted', 'fitted in build')))
        key = (c['part_number'], c['manufacturer'], c['component_type'], c['package_type'], flags,
               c['confidence']) if c['part_number'] and c['manufacturer'] else id(c)
        if key not in groups:
            groups[key] = {**c, 'reference_designator': [c['reference_designator']], 'pages': {c['page_number']}}
            order.append(key)
        else:
            g = groups[key]
            if c['reference_designator'] not in g['reference_designator']:
                g['reference_designator'].append(c['reference_designator'])
                if len(g.get('locations', [])) < 200:
                    g['locations'] = g.get('locations', []) + c.get('locations', [])
            g['pages'].add(c['page_number'])
    out = []
    for key in order:
        g = groups[key]
        refs = g.pop('reference_designator')
        pages = sorted(g.pop('pages'))
        g.update(reference_designator=', '.join(refs), quantity=len(refs), page_number=pages[0])
        if len(pages) > 1:
            g['extraction_context'] += f" (pages {', '.join(map(str, pages))})"
        out.append(g)
    return out


# Rendering at 300 DPI and running Tesseract OCR per page is genuinely slow
# (multiple seconds/page) and runs synchronously in the request cycle - this
# bounds the worst case for a moderator OCR-scanning an oversized manual
# rather than leaving it fully unbounded. Pages read from the PDF's text layer
# don't count: they take milliseconds.
MAX_OCR_PAGES = 30


def build_candidates_from_schematic_file(file_obj, file_type):
    """
    Run OCR extraction across every page/image of a schematic file.

    file_type: 'pdf' renders each page at 300 DPI first; image types
    (png/jpg/etc) are OCR'd directly.
    """
    from PIL import Image

    candidates = []
    file_obj.seek(0)
    raw = file_obj.read()

    if file_type == 'pdf':
        import pdf2image
        # Reading the text layer is cheap, so every page is read first; only the
        # pages without one need the expensive render+OCR, and only they count
        # towards the limit - checked before any of that work starts.
        layers = _text_layers(raw)
        from .schematic_values import detect_odm
        odm = detect_odm(' '.join(w['text'] for words in layers for w in words))   # whose size codes apply
        scanned = [n for n, words in enumerate(layers, start=1) if len(words) < MIN_TEXT_LAYER_WORDS]
        if len(scanned) > MAX_OCR_PAGES:
            raise ValueError(
                f'PDF has {len(scanned)} scanned pages (pages without a text layer) - OCR is limited to '
                f'{MAX_OCR_PAGES} of them. Split the PDF and upload a smaller '
                f'excerpt as its own schematic if you need to OCR more of it.'
            )
        for page_number, words in enumerate(layers, start=1):
            if page_number in scanned:
                # one page at a time: a whole manual rendered at 300 DPI won't fit in memory
                image = pdf2image.convert_from_bytes(raw, dpi=300, first_page=page_number,
                                                     last_page=page_number)[0]
                candidates.extend(extract_candidates_from_page(image, page_number, odm=odm))
            else:
                candidates.extend(extract_candidates_from_page(None, page_number, words, source='PDF text', odm=odm))
    else:
        image = Image.open(io.BytesIO(raw))
        candidates.extend(extract_candidates_from_page(image, 1))

    return candidates
