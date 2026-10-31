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


def extract_candidates_from_page(image, page_number, words=None, source='OCR'):
    """Designator/nearby-value candidates on one page: OCR'd from its rendered image, or
    `words` already read from the PDF's text layer."""
    strict = words is not None
    if words is None:
        words = _ocr_image(image)
    candidates = []
    used = set()
    seen_designators = set()

    for i, w in enumerate(words):
        if not REF_DES_PATTERN.fullmatch(w['text']):
            continue
        if w['text'] in seen_designators:
            continue  # same designator OCR'd twice on one page - keep first
        if strict and not DESIGNATOR_PREFIX.match(w['text']):
            continue
        seen_designators.add(w['text'])

        value_index = _nearest_value(i, words, used, strict)
        if strict and value_index is None:
            continue  # a pin or ball name: real parts on a CAD page have their value printed beside them
        value_text = ''
        if value_index is not None:
            used.add(value_index)
            value_text = words[value_index]['text']

        candidates.append({
            'page_number': page_number,
            'confidence': 'low',
            'reference_designator': w['text'],
            'part_number': value_text,
            'manufacturer': '',
            'component_type': (classify_component_type(value_text) if value_text else '') if not strict else (
                next((t for t in [classify_component_type(value_text)] if t and t != 'other'), '')
                or designator_type(w['text'])),
            'package_type': '',
            'description': '',
            'value_raw': value_text,
            'quantity': 1,
            'location_description': '',
            'extraction_context': (
                f"{source}: designator '{w['text']}' near text '{value_text}'"
                if value_text else f"{source}: designator '{w['text']}', no nearby text found"
            ),
        })
    return candidates


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
                candidates.extend(extract_candidates_from_page(image, page_number))
            else:
                candidates.extend(extract_candidates_from_page(None, page_number, words, source='PDF text'))
    else:
        image = Image.open(io.BytesIO(raw))
        candidates.extend(extract_candidates_from_page(image, 1))

    return candidates
