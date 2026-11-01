"""
Tests for parts_list_utils: service-manual parts lists read from pdftotext -layout.
"""
import io

import pytest

from apps.products import parts_list_utils as pl

SONY = '\n'.join(f'R{100 + i}      1-216-8{20 + i}-11     METAL CHIP     {i + 1}K     5%     1/10W' for i in range(10))
SAMSUNG = '\n'.join(f'2007-0080{50 + i}      R{4001 + i},R{4101 + i}      R-CHIP;{i + 1}Kohm,5%,1/16W,TP,1005'
                    for i in range(10))
YAMAHA_TWO_TABLES = '\n'.join(f'C{170 + i} ZD5176{i}0 C.MYLAR 100pF 100V      R{300 + i} RD35{i % 4 + 4}100 R.CHP 1KΩ 1/16W J ⚠'
                              for i in range(10))
FACTORY = '\n'.join(f'SE0000155{i}0     S CER CAP 47U 6.3V M X5R 0603     CH4{i} CT33{i}' for i in range(10))


def test_the_three_row_shapes():
    assert pl.parse_page(SONY)[0] == ('1-216-820-11', ['R100'], 'METAL CHIP 1K 5% 1/10W')
    assert pl.parse_page(SAMSUNG)[0] == ('2007-008050', ['R4001', 'R4101'], 'R-CHIP;1Kohm,5%,1/16W,TP,1005')
    rows = pl.parse_page(YAMAHA_TWO_TABLES)
    assert ('ZD517600', ['C170'], 'C.MYLAR 100pF 100V') in rows and len(rows) == 20       # two tables per line
    assert pl.parse_page(FACTORY)[0] == ('SE000015500', ['CH40', 'CT330'], 'S CER CAP 47U 6.3V M X5R 0603')


def test_a_document_needs_a_real_parts_list():
    rows, why = pl.parse_document([SONY, SONY + '\n' + SONY])
    assert len(rows) == 30
    assert pl.parse_document([SONY])[0] == []                        # 10 rows: not a parts list
    schematic_labels = '\n'.join(f'R{i}      0.1U_0402_16V7K      NET{i}' for i in range(30))
    assert pl.parse_document([schematic_labels])[0] == []


def test_rows_become_typed_suggestions(monkeypatch):
    monkeypatch.setattr(pl, '_layout_pages', lambda raw: [SONY, SONY.replace('R1', 'R2')])
    rows = pl.build_candidates_from_parts_list(io.BytesIO(b'%PDF'), 'Sony')
    first = rows[0]
    assert (first['part_number'], first['manufacturer'], first['component_type'], first['confidence']) == \
        ('1-216-820-11', 'Sony', 'resistor', 'high')
    monkeypatch.setattr(pl, '_layout_pages', lambda raw: [YAMAHA_TWO_TABLES])     # one manual, one code shape
    rows = pl.build_candidates_from_parts_list(io.BytesIO(b'%PDF'), 'Yamaha')
    yamaha_r = next(r for r in rows if r['part_number'].startswith('RD35'))
    assert yamaha_r['component_type'] == 'resistor'
    assert 'safety-critical' in yamaha_r['description'] and '⚠' not in yamaha_r['description']


@pytest.mark.django_db
def test_manuals_without_a_parts_list_fall_back(monkeypatch):
    monkeypatch.setattr(pl, '_layout_pages', lambda raw: ['just some prose'])
    called = []
    monkeypatch.setattr('apps.products.pdf_bom_utils.build_candidates_from_pdf', lambda f: called.append(1) or [])
    assert pl.extract_manual_candidates(io.BytesIO(b'%PDF'), 'Sony') == [] and called == [1]


@pytest.mark.django_db
def test_scans_are_open_cached_and_only_new_ones_limited(monkeypatch, product, user):
    from django.core.cache import cache
    from django.core.files.base import ContentFile
    from rest_framework.test import APIClient
    from apps.api import throttling
    from apps.products.models import Schematic

    cache.clear()
    schematic = Schematic(product=product, title='Manual', schematic_type='service_manual', file_type='pdf',
                          is_approved=True, uploaded_by=user)
    schematic.file.save('manual.pdf', ContentFile(b'%PDF'), save=True)
    runs = []
    monkeypatch.setattr(pl, '_layout_pages', lambda raw: runs.append(1) or [SONY, SONY.replace('R1', 'R2')])
    monkeypatch.setattr(throttling.ExtractionAnonRateThrottle, 'get_rate', lambda self: '1/hour')
    url = f'/api/schematics/{schematic.pk}/extract_bom/'
    visitor = APIClient()                                             # not signed in
    assert visitor.get(url).status_code == 200 and visitor.get(url).status_code == 200
    assert len(runs) == 1                                             # the second view came from the cache
    other = Schematic(product=product, title='Other', schematic_type='service_manual', file_type='pdf',
                      is_approved=True, uploaded_by=user)
    other.file.save('other.pdf', ContentFile(b'%PDF'), save=True)
    assert visitor.get(f'/api/schematics/{other.pk}/extract_bom/').status_code == 429   # a new scan: limited


VAIO = '\n'.join(f'C{50 + i}     A     41.7500     32.8500    6E5                2200pF   6.3V     10%    1128628{10 + i}   '
                  f'CAP, CERAMIC 2200PF B (0603)   DNI' for i in range(10))
ONKYO = '\n'.join(f'R{464 + i}   C-CARBON R   RN72K1J-181JE   1   43503181{i}R1' for i in range(10))
PSP = '\n'.join(f'U    C{1064 + i}\t\t               CERAMIC CHIP    0.1uF     10%   10V' for i in range(10))


def test_tables_with_the_code_further_along():
    row = pl.parse_page_late(VAIO)[0]
    assert row == ('112862810', ['C50'], '2200pF 6.3V 10% CAP, CERAMIC 2200PF B (0603) (not fitted)')
    assert pl.parse_page_late(ONKYO)[0] == ('435031810R1', ['R464'], 'C-CARBON R RN72K1J-181JE')    # after the qty
    assert pl.parse_page_late(PSP)[0] == ('', ['C1064'], 'CERAMIC CHIP 0.1uF 10% 10V')    # unsupplied: no code


def test_late_tables_and_related_code_shapes_pass_the_document_checks():
    assert len(pl.parse_document([VAIO, VAIO, VAIO])[0]) == 30
    panasonic = '\n'.join(f'C{1015 + i}    F1H1H10{i}B047   0.1uF      50V    1' for i in range(8)) + '\n' + \
        '\n'.join(f'R{1015 + i}    ERJ2GEJ10{i}X   10K      1/16W    1' for i in range(4))
    rows, why = pl.parse_document([panasonic, panasonic])
    assert len(rows) == 24, why                                         # two code shapes, one maker


def test_unsupplied_parts_become_generic_parts(monkeypatch):
    monkeypatch.setattr(pl, '_layout_pages', lambda raw: [PSP, PSP, PSP])
    row = pl.build_candidates_from_parts_list(io.BytesIO(b'%PDF'), 'Sony')[0]
    assert (row['part_number'], row['manufacturer']) == ('CAP 100nF 10V 10%', 'Generic')


def test_sony_prints_micro_as_m(monkeypatch):
    sony = '\n'.join(f'C{100 + i}     1-12{i}-960-11     CERAMIC CHIP     0.1MF     10%     16V' for i in range(10))
    monkeypatch.setattr(pl, '_layout_pages', lambda raw: [sony, sony.replace('C1', 'C2'), sony.replace('C1', 'C3')])
    row = pl.build_candidates_from_parts_list(io.BytesIO(b'%PDF'), 'Sony')[0]
    assert row['description'].startswith('CERAMIC CHIP 0.1uF')
