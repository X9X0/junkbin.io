"""
Schematic OCR extraction utilities.

Circuit diagrams (full schematics, block diagrams, PCB layouts, wiring
diagrams) don't have textual BOM tables - their components are drawn
symbols with reference-designator labels scattered spatially across the
page, not listed anywhere in reading order. This renders each page to an
image and OCRs it with Tesseract, then looks for designator-shaped tokens
and whatever text sits nearest to them on the page as a rough stand-in
for "the marking printed next to this part."

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


def _nearest_value(designator_index, words, used_indices):
    """Find the closest other word to a designator, ignoring noise/used tokens."""
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
        dist = math.hypot(w['x'] - d['x'], w['y'] - d['y'])
        if dist > MAX_PAIR_DISTANCE_PX:
            continue
        if best_dist is None or dist < best_dist:
            best_index = i
            best_dist = dist
    return best_index


def extract_candidates_from_page(image, page_number):
    """OCR one rendered page and return designator/nearby-value candidates."""
    words = _ocr_image(image)
    candidates = []
    used = set()
    seen_designators = set()

    for i, w in enumerate(words):
        if not REF_DES_PATTERN.fullmatch(w['text']):
            continue
        if w['text'] in seen_designators:
            continue  # same designator OCR'd twice on one page - keep first
        seen_designators.add(w['text'])

        value_index = _nearest_value(i, words, used)
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
            'component_type': classify_component_type(value_text) if value_text else '',
            'package_type': '',
            'description': '',
            'value_raw': value_text,
            'quantity': 1,
            'location_description': '',
            'extraction_context': (
                f"OCR: designator '{w['text']}' near text '{value_text}'"
                if value_text else f"OCR: designator '{w['text']}', no nearby text found"
            ),
        })
    return candidates


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
        pages = pdf2image.convert_from_bytes(raw, dpi=300)
        for page_number, image in enumerate(pages, start=1):
            candidates.extend(extract_candidates_from_page(image, page_number))
    else:
        image = Image.open(io.BytesIO(raw))
        candidates.extend(extract_candidates_from_page(image, 1))

    return candidates
