"""
Tests for schematic_ocr_utils: CAD-exported pages are read from the PDF's text layer (no OCR,
no page limit); only pages without one are OCR'd and counted against MAX_OCR_PAGES.
"""
import io

import pytest
from PIL import Image

from apps.products import schematic_ocr_utils as ocr


def _text_pdf(pages):
    """A minimal PDF whose pages carry real text: pages = [[(x, y, text), ...], ...]."""
    objects = ['<< /Type /Catalog /Pages 2 0 R >>', None,
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    for words in pages:
        stream = ''.join(f'BT /F1 8 Tf {x} {y} Td ({text}) Tj ET\n' for x, y, text in words)
        objects.append(f'<< /Length {len(stream)} >>\nstream\n{stream}endstream')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
                       f'/Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>')
        kids.append(len(objects))
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    out, offsets = b'%PDF-1.4\n', []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f'{n} 0 obj\n{body}\nendobj\n'.encode()
    xref = len(out)
    out += f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode()
    out += ''.join(f'{o:010d} 00000 n \n' for o in offsets).encode()
    out += f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return io.BytesIO(out)


# a laptop schematic's page: parts with their values beside them, BGA balls beside net names,
# stuffing-option markers, rails
CAD_PAGE = [(100, 700, 'C142'), (100, 690, '0.01U_0402_16V7K'), (100, 650, 'R141'), (123, 650, '@'),
            (100, 640, '0_0805_5%'), (300, 600, 'AK57'), (322, 600, 'SB_DQ3'), (300, 500, 'CV1'),
            (318, 500, 'PX@'), (300, 490, '1U_0402_6.3V6K'), (100, 400, 'T2'), (115, 400, 'H_PROCHOT#_R'),
            (300, 300, 'PQ301'), (330, 300, '+3VALW'), (300, 290, 'AON7408L_DFN8-5')] + \
           [(50, 100 + 10 * i, f'NET{i}') for i in range(10)]


def test_text_layer_pages_are_read_without_ocr(monkeypatch):
    monkeypatch.setattr(ocr, '_ocr_image', lambda image: pytest.fail('a page with a text layer was OCR\'d'))
    candidates = ocr.build_candidates_from_schematic_file(_text_pdf([CAD_PAGE]), 'pdf')
    found = {c['reference_designator']: (c['part_number'], c['component_type']) for c in candidates}
    assert found == {
        'C142': ('0.01U_0402_16V7K', 'capacitor'),
        'R141': ('0_0805_5%', 'resistor'),              # not the '@' option marker
        'CV1': ('1U_0402_6.3V6K', 'capacitor'),         # not 'PX@'
        'PQ301': ('AON7408L_DFN8-5', 'transistor'),     # not the '+3VALW' rail
    }                                                   # no BGA ball (AK57) or test point beside a net (T2)
    assert candidates[0]['extraction_context'].startswith('PDF text:')


def test_only_scanned_pages_count_towards_the_ocr_limit(monkeypatch):
    monkeypatch.setattr(ocr, 'MAX_OCR_PAGES', 1)
    many = _text_pdf([CAD_PAGE] * 3)                    # three text pages: well past the limit, all read
    monkeypatch.setattr(ocr, '_ocr_image', lambda image: pytest.fail('OCR ran'))
    assert len(ocr.build_candidates_from_schematic_file(many, 'pdf')) == 12

    scans = io.BytesIO()
    Image.new('RGB', (200, 200), 'white').save(scans, 'PDF', save_all=True,
                                               append_images=[Image.new('RGB', (200, 200), 'white')])
    with pytest.raises(ValueError, match='2 scanned pages'):
        ocr.build_candidates_from_schematic_file(scans, 'pdf')


@pytest.mark.django_db
def test_ocr_labels_match_catalog_parts_exactly(component_factory):
    from apps.products.pdf_bom_utils import match_components_exactly
    part = component_factory(manufacturer='Richtek', part_number='RT8207PGQW')
    component_factory(manufacturer='Yageo', part_number='RC0402JR-0710K_0402L')
    found = match_components_exactly([{'part_number': 'rt8207pgqw'}, {'part_number': '10K_0402'}, {'part_number': ''}])
    assert [c['matched_component'] and c['matched_component']['id'] for c in found] == [str(part.pk), None, None]
