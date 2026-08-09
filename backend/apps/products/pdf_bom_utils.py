"""
PDF/manual BOM extraction utilities.

Extracts candidate component rows from an uploaded PDF manual or service
document. Tries structured table extraction first (high confidence, reuses
the same column-alias detection as the CSV BOM importer), then falls back
to a heuristic line-by-line text scan (low confidence) on any page a table
didn't already cover.

Every candidate is a suggestion, never written directly into the live
parts list - see ComponentSuggestion / apps.products.views for the
moderation-gated review flow this feeds.
"""
import re

from .bom_utils import (
    detect_column_mapping,
    validate_row,
    classify_component_type,
    extract_package,
)

# Reference designator: 1-3 letters + 1-4 digits, e.g. U3, R12, C104, Q1, J2
REF_DES_PATTERN = re.compile(r'\b([A-Z]{1,3}\d{1,4})\b')

# Last-resort "looks like a part number" token: alnum with at least one
# digit, at least 4 chars, optionally hyphenated/slashed.
PART_NUMBER_PATTERN = re.compile(r'\b(?=[A-Z0-9\-/.]*\d)[A-Z0-9][A-Z0-9\-/.]{3,}\b')

MAX_LINE_LENGTH = 200


def _extract_tables(pdf):
    """Find every table on every page whose header row looks like a BOM."""
    found = []
    for page_num, page in enumerate(pdf.pages, start=1):
        for table in page.extract_tables():
            if not table or len(table) < 2:
                continue
            headers = [str(h or '').strip() for h in table[0]]
            mapping = detect_column_mapping(headers)
            if 'part_number' not in mapping.values():
                continue  # doesn't look like a BOM table, skip
            rows = []
            for raw_row in table[1:]:
                row_dict = {
                    headers[i]: str(raw_row[i] or '').strip()
                    for i in range(min(len(headers), len(raw_row)))
                }
                if any(row_dict.values()):
                    rows.append(row_dict)
            if rows:
                found.append({
                    'page_number': page_num,
                    'mapping': mapping,
                    'rows': rows,
                })
    return found


def _extract_text_candidates(pdf, skip_pages):
    """Heuristic fallback: lines containing both a ref designator and a
    plausible part-number-ish token, on pages with no recognized table."""
    candidates = []
    for page_num, page in enumerate(pdf.pages, start=1):
        if page_num in skip_pages:
            continue
        text = page.extract_text() or ''
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) > MAX_LINE_LENGTH:
                continue
            ref_match = REF_DES_PATTERN.search(line)
            if not ref_match:
                continue
            rest = line[ref_match.end():]
            part_match = PART_NUMBER_PATTERN.search(rest)
            if not part_match:
                continue
            # Lines listing several reference designators together (e.g.
            # "SW19,SW18,SW17,...") match REF_DES_PATTERN repeatedly and
            # would otherwise get treated as one designator "using" the
            # next as its part number. A real part number is never shaped
            # exactly like a bare reference designator, so reject those.
            if REF_DES_PATTERN.fullmatch(part_match.group(0)):
                continue
            candidates.append({
                'page_number': page_num,
                'reference_designator': ref_match.group(1),
                'part_number': part_match.group(0),
                'raw_line': line,
            })
    return candidates


def build_candidates_from_pdf(file_obj):
    """
    Run the full extraction pipeline on an uploaded PDF file.

    Returns a list of normalized candidate dicts, each with a 'confidence'
    key ('high' for table rows, 'low' for heuristic text matches).
    """
    import pdfplumber

    candidates = []

    file_obj.seek(0)
    with pdfplumber.open(file_obj) as pdf:
        tables = _extract_tables(pdf)
        covered_pages = {t['page_number'] for t in tables}

        for table in tables:
            for raw_row in table['rows']:
                cleaned, _errors = validate_row(raw_row, table['mapping'])
                if not cleaned.get('part_number'):
                    continue
                description = cleaned.get('description', '')
                comp_type = cleaned.get('component_type') or classify_component_type(description)
                pkg = cleaned.get('package_type') or extract_package(description)
                candidates.append({
                    'page_number': table['page_number'],
                    'confidence': 'high',
                    'part_number': cleaned.get('part_number', ''),
                    'manufacturer': cleaned.get('manufacturer', ''),
                    'reference_designator': cleaned.get('reference_designator', ''),
                    'component_type': comp_type,
                    'package_type': pkg,
                    'description': description,
                    'value_raw': cleaned.get('value', ''),
                    'quantity': cleaned.get('quantity', 1),
                    'location_description': cleaned.get('location_description', ''),
                    'extraction_context': ' | '.join(f'{k}: {v}' for k, v in raw_row.items() if v),
                })

        for line_candidate in _extract_text_candidates(pdf, covered_pages):
            raw_line = line_candidate['raw_line']
            candidates.append({
                'page_number': line_candidate['page_number'],
                'confidence': 'low',
                'part_number': line_candidate['part_number'],
                'manufacturer': '',
                'reference_designator': line_candidate['reference_designator'],
                'component_type': classify_component_type(raw_line),
                'package_type': extract_package(raw_line),
                'description': '',
                'value_raw': '',
                'quantity': 1,
                'location_description': '',
                'extraction_context': raw_line,
            })

    return candidates


def find_component_match(part_number, manufacturer=''):
    """Best-effort match against the existing Component catalog."""
    from apps.components.models import Component

    if not part_number:
        return None

    qs = Component.objects.all()
    if manufacturer:
        exact = qs.filter(part_number__iexact=part_number, manufacturer__iexact=manufacturer).first()
        if exact:
            return exact

    exact_pn = qs.filter(part_number__iexact=part_number).first()
    if exact_pn:
        return exact_pn

    return qs.filter(part_number__icontains=part_number).first()
