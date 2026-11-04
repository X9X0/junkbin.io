"""
Tests for parts_list_utils: service-manual parts lists read from pdftotext -layout.
"""
import collections
import io
import json
from pathlib import Path

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


def test_tpv_codes_and_their_related_shapes():
    """Sharp/Philips TV chassis (TPV): codes in a few shapes of one family, a vendor mark after the code."""
    page = '\n'.join([f'R{1006 + i}     061G0402220 JY   RST CHIPR 22 OHM +-5% 1/16W YAGEO      -     --' for i in range(6)]
                     + [f'C{626 + i}      065G060310522KA    CAP 0603 1UF 10% 25V X7R    -     --' for i in range(4)]
                     + [f'D{401 + i}      093G 64S526SEM     SWITCHING BAS316WS 250MA 100V SOD323       -     --'
                        for i in range(2)])
    rows, why = pl.parse_document([page, page])
    assert len(rows) == 24, why
    assert rows[0][1:] == ('061G0402220', ['R1006'], 'RST CHIPR 22 OHM +-5% 1/16W YAGEO')
    assert ('093G64S526SEM', ['D401'], 'SWITCHING BAS316WS 250MA 100V SOD323') in [r[1:] for r in rows]


PAGES = json.load(open(Path(__file__).parent / 'fixtures' / 'parts_list_pages.json', encoding='utf-8'))


@pytest.mark.parametrize('name', sorted(PAGES))
def test_real_parts_list_pages(name):
    """40 lines of a real parts-list page per layout (Sharp/TPV, Panasonic, Onkyo, Sony VAIO, Sony PSP,
    LG phones):
    the number of rows and the first one must not change unnoticed."""
    page = PAGES[name]
    rows = pl.page_rows(page['page'])
    assert len(rows) == page['rows']
    assert [rows[0][0], rows[0][1], rows[0][2]] == page['first']


def test_indexed_rows_take_wrapped_locations_up_to_their_quantity():
    rows = pl.page_rows(PAGES['lg_wrapped']['page'])
    assert ('EAG64672301', ['ANT1005', 'ANT1006', 'ANT1007', 'ANT1008', 'ANT1009', 'ANT1010', 'ANT1011',
                            'ANT5100', 'ANT5101'], 'C-Clip') in rows


def test_positions_printed_with_a_space_and_three_digit_sharp_codes():
    rows = pl.page_rows(PAGES['sharp_spaced']['page'])
    assert ('RH-EXA741WJQZY', ['D3807'], 'ZENER DIODE 5.6V DZ2J056MOL(PANASONIC)') in rows
    assert ('RBLN-A528WJZZY', ['FB1102'], 'FERRITA HI0805N600R-10') in rows
    # a word and a number that are not a position stay apart: 'EN 300 744' is not a row
    assert pl.parse_page('DVB-T (ETSI EN 300 744) demodulator & FEC decoder.') == []


def test_sharp_mark_and_price_columns_are_not_description():
    assert pl._tidy('VCKYCY1EF104ZY', '0.1 25V Ceramic J AA AA') == '0.1 25V Ceramic'
    assert pl._tidy('RC-KZA073WJZZY', 'AD J Capacitor, 10 16V Ceramic') == 'Capacitor, 10 16V Ceramic'
    assert pl._tidy('QACCBA073WJPZ', 'J AC Cord for U.K.') == 'J AC Cord for U.K.'
    assert pl._tidy('X', 'BATTERY SIZE AA') == 'BATTERY SIZE AA'
    assert pl._tidy('GH59-14987A', 'F I LTE R - S AW') == 'F I LTE R - S AW'



def test_sharp_two_column_rows_with_safety_marks_lugs_and_lowercase_codes():
    # Sharp LC-32LE600E parts list (two columns per line); each second-column row used to be read into the
    # first row's description
    page = '\n'.join([
        '      FB4603    RBLN-0210TAZZY    Ferrite Bead         J   AB      AB         L1900     RCiLFA134WJZZY     Coil'
        '                    J   AF      AF',
        'R1909     VRS-CY1JF561JY   560 1/16W Metal Oxide    J   AA      AA      LUG1902   QLUGHA009WJZZY    Lug'
        '                         J   AC     AC',
        '       C712        RC-E1H226SNKY       22 KY 50V Electrolytic                     J    --      --     ! C806'
        '      RC-M2E473RESC   0.047 RE473C 275V Film     J    --      --',
        '! C841        RC-CSE2GA332M   3300p CS 250V Ceramic                     J    --      --         R761'
        '      VRS-TS2AD151J   150 1/8W Resistor                           J   --      --',
        'R1905   VRS-TV1JD750JY   75 1/16W Metal Oxide     J   AA      AA         SC1901 QSOCZA110WJZZQ Socket, 19Pin'
        '                   J    --        --',
    ])
    assert pl.parse_page(page) == [
        ('RBLN-0210TAZZY', ['FB4603'], 'Ferrite Bead'), ('RCiLFA134WJZZY', ['L1900'], 'Coil'),
        ('VRS-CY1JF561JY', ['R1909'], '560 1/16W Metal Oxide'), ('QLUGHA009WJZZY', ['LUG1902'], 'Lug'),
        ('RC-E1H226SNKY', ['C712'], '22 KY 50V Electrolytic'), ('RC-M2E473RESC', ['C806'], '⚠ 0.047 RE473C 275V Film'),
        ('RC-CSE2GA332M', ['C841'], '⚠ 3300p CS 250V Ceramic'), ('VRS-TS2AD151J', ['R761'], '150 1/8W Resistor'),
        ('VRS-TV1JD750JY', ['R1905'], '75 1/16W Metal Oxide'), ('QSOCZA110WJZZQ', ['SC1901'], 'Socket, 19Pin'),
    ]
    assert not pl.REFDES_RE.match('SC70')         # a package, not a socket position



def test_sharp_fixed_width_codes_and_r_mark():
    # Sharp LC-32LE600E: semiconductor and resistor codes padded to 13-14 characters, few digits
    page = '\n'.join([
        '      R879      VRS-TS2AD221J   220 1/8W Resistor                        J    --      --         D7501     '
        'VHDDAN217u/-1    DAN217u 80V/100mA                             J    --      --',
        'C7525     VCKYCY1HB682K   6800p 50V Ceramic    J    --      --         Q7601     VSUM6K1N///-1      '
        'UM6K1N 30V/100mA                J   --      --',
        '  C818        VCKYCY1HB103K   0.01 50V Ceramic                          J    --      --         R745      '
        'VRS-TP2BD3R3J   3.3 1/4W Resistor                           J   --      --',
    ])
    assert pl.parse_page(page) == [
        ('VRS-TS2AD221J', ['R879'], '220 1/8W Resistor'), ('VHDDAN217u/-1', ['D7501'], 'DAN217u 80V/100mA'),
        ('VCKYCY1HB682K', ['C7525'], '6800p 50V Ceramic'), ('VSUM6K1N///-1', ['Q7601'], 'UM6K1N 30V/100mA'),
        ('VCKYCY1HB103K', ['C818'], '0.01 50V Ceramic'), ('VRS-TP2BD3R3J', ['R745'], '3.3 1/4W Resistor'),
    ]
    for code in ('VHiNJM2584M-1Y', 'VHD1SS390++-1Y', 'VCFYFA1HA334J+', 'RCiLP0343TAZZY', 'RR-HRSM1R5J3W'):
        assert pl.SHARP_CODE.match(code), code
    for word in ('VALUE-1234567', 'RESISTOR12345', 'VCC3P3'):
        assert not pl.SHARP_CODE.match(word), word
    # Sharp LC-26SH12E and others mark with R: 'R745  VRS-TV1JD103JY  AA  R  Resistor, 10k 1/16W Metal Oxide'
    assert pl._tidy('VCKYCY1HB392KY', 'AA R Capacitor, 3900p 50V Ceramic') == 'Capacitor, 3900p 50V Ceramic'


def test_sharp_codes_count_as_one_family():
    # the code shapes of Sharp LC-42SA1E page 124: without the WJ codes counted as one family the top three
    # shapes hold 30 of 55 rows (< 70%) and the page was dropped
    codes = (['VS2SA1037R/-1', 'VS2SC2412K/-1', 'VSDTA114EK/-1'] * 6 + ['RH-EXA103WJZZY'] * 9
             + ['VHD1SS355//-1Y'] * 9 + ['VHDHSU119//-1Y'] * 8 + ['QPLGNA341WJZZY'] * 7 + ['VRS-CY1JF000JY'] * 4)
    rows = [(c, ['D1'], 'x') for c in codes]
    assert pl._page_kept(rows)
    assert (sum(v for _, v in collections.Counter(pl.shape(c) for c in codes).most_common(3)) / len(codes)
            < pl.MIN_SHAPE_SHARE)


def test_indexed_locations_cut_inside_a_position_and_code_beside_description():
    rows = {r[0]: r for r in pl.page_rows(PAGES['lg_cut_locations']['page'])}
    refs = rows['ECCH0009101'][1]          # '...,C2344,C2' / '347,C2349,...' / ',C5004,...'
    assert len(refs) == 47 and 'C2347' in refs and 'C2' not in refs
    assert rows['ECCH0007804'] == ('ECCH0007804', ['C3012', 'C4031', 'C4131', 'C4132', 'C4133', 'C4134', 'C4135',
                                                   'C4137', 'C4138', 'C4142'], 'Capacitor,Ceramic,Chip')


def test_section_heading_read_onto_the_row_above_is_dropped():
    assert pl._tidy('X', 'C CERAM 0402 100NF 25V 20% RESISTORS') == 'C CERAM 0402 100NF 25V 20%'
    assert pl._tidy('X', 'Zener Diode J AA AA TRANSISTORS') == 'Zener Diode'


@pytest.mark.parametrize('desc,clean', [
    ('0.1 25V Ceramic', '0.1uF 25V Ceramic'),
    ('Capacitor, 47 16V Electrolytic', 'Capacitor, 47uF 16V Electrolytic'),
    ('82 KXG 450V Electrolytic J', '82uF KXG 450V Electrolytic J'),
    ('0,047 100V Ceramic J', '0.047uF 100V Ceramic J'),
    ('22p 50V Ceramic', '22p 50V Ceramic'),              # pF is marked
])
def test_sharp_bare_capacitances_are_microfarads(desc, clean):
    assert pl.BARE_MICROFARADS.sub(pl._microfarads, desc) == clean


@pytest.mark.parametrize('desc,clean', [
    # the kind first (Sharp LC-32LE600E, an Asus-family list; their codes give the same values: VCKYCY1EF104ZY,
    # UA354680 = 680 x 10^2 pF)
    ('Ceramic 0.1 25V R', 'Ceramic 0.1uF 25V R'),
    ('Electrolytic Cap. 22.00 16.0V 01', 'Electrolytic Cap. 22.00uF 16.0V 01'),
    ('Mylar Capacitor 0.0680 50V J 01', 'Mylar Capacitor 0.0680uF 50V J 01'),
    ('Ceramic Capacitor-B (chip) 0.0100 50V K 01', 'Ceramic Capacitor-B (chip) 0.0100uF 50V K 01'),
    ('Capacitor, 0.22 50V', 'Capacitor, 0.22uF 50V'),
    ('Ceramic Capacitor-B (chip) 1000P 50V K 01', 'Ceramic Capacitor-B (chip) 1000P 50V K 01'),
])
def test_bare_microfarads_after_the_kind(desc, clean):
    assert pl.BARE_MICROFARADS_AFTER.sub(pl._microfarads_after, desc) == clean


@pytest.mark.parametrize('desc,clean', [
    ('AA R Capacitor, 3900p 50V Ceramic', 'Capacitor, 3900p 50V Ceramic'),
    ('AB N J Capacitor 4.7 10V Ceramic', 'Capacitor 4.7 10V Ceramic'),
    ('N J Capacitor 0.22 50V', 'Capacitor 0.22 50V'),
    ('J Capacitor, 0.22 50V', 'Capacitor, 0.22 50V'),
    ('R Coil', 'Coil'),
    ('J AC Cord for U.K.', 'J AC Cord for U.K.'),
    ('F I LTE R - S AW', 'F I LTE R - S AW'),
])
def test_sharp_mark_columns_before_the_description(desc, clean):
    assert pl._tidy('X', desc) == clean


@pytest.mark.parametrize('desc,clean', [
    ('CAPACITOR GRM39F 104Z 25 (1608)SMD', 'CAPACITOR GRM39F 100000PF Z 25V (1608)SMD'),
    ('CAPACITOR GRM39CK 180J 50 (1608)SMD', 'CAPACITOR GRM39CK 18PF J 50V (1608)SMD'),
    ('CONDENSADOR GRM39B 105K 6.3 (1608)SMD', 'CONDENSADOR GRM39B 1000000PF K 6.3V (1608)SMD'),
])
def test_murata_coded_capacitances(desc, clean):
    assert pl.MURATA_CODED.sub(pl._murata_coded, desc) == clean


@pytest.mark.parametrize('desc,kind,specs', [
    # Onkyo TX-SR507 / HT-R960 parts lists
    ('C-CARBON R RN72K1J-331JE', 'resistor', {'resistance_ohm': 330.0, 'tolerance': '5%'}),
    ('CARBON R R16J-2.2K', 'resistor', {'resistance_ohm': 2200.0}),
    ('NF CARBON R R25J-0.22', 'resistor', {'resistance_ohm': 0.22}),
    ('C-CERA C CK725B1H-103K1', 'capacitor', {'capacitance_pf': 10000.0, 'voltage_v': 50.0, 'tolerance': '10%'}),
    ('C-CERA C CC725CH1H-060D1', 'capacitor', {'capacitance_pf': 6.0, 'voltage_v': 50.0, 'tolerance': '±0.5pF'}),
    ('CERA C CK45F50V-223Z', 'capacitor', {'capacitance_pf': 22000.0, 'voltage_v': 50.0, 'tolerance': '+80/-20%'}),
    ('UTSP C CE04W50V-10M(UTSP)', 'capacitor', {'capacitance_pf': 1e7, 'voltage_v': 50.0, 'tolerance': '20%'}),
    # zero-ohm links (Sony, TPV) and TPV's RKM inductances
    ('1A CONDUCTOR, CHIP (1005)', 'resistor', {'resistance_ohm': 0.0}),
    ('RST CHIPR MAX0R05 1/16W FENGHUA', 'resistor', {'resistance_ohm': 0.0}),
    ('9JR7300000056 CHIP INDUCTOR 1U8 10% FCI1608F-1R8K 1', 'inductor', {'inductance_uh': 1.8, 'tolerance': '10%'}),
])
def test_maker_value_forms(desc, kind, specs):
    from apps.components.spec_parse import parse_description
    got = parse_description(pl.clean_description(desc), kind)[1]
    assert {k: got.get(k) for k in specs} == specs


def test_marking_code_book_is_not_a_parts_list():
    # 'SMD semiconductor codes 2012': the marking stands where a position would, and repeats down the page
    marks = ['B0', 'B0', 'B0', 'B5', 'B5', 'B5', 'E11', 'L65', 'L65', 'L65']
    lines = [f'{m}      {p}{n:04d}C-10PC     Vdet-IC 1.{n % 9}V, -Reset PPO        SOT-23    16vda'
             for n, (m, p) in enumerate((m, p) for p in ('AP', 'LN', 'XC') for m in marks)]
    page = '\n'.join(lines)
    assert len(pl.page_rows(page)) == 30
    rows, why = pl.parse_document([page])
    assert rows == [] and 'code table' in why


def test_every_sharp_code_stays_with_the_family():
    # VS2SA1530AR-1Y has 4 digits: it keeps its own shape in the count, but is never dropped as an odd shape
    assert pl.SHARP_FAMILY.match('VS2SA1530AR-1Y') and not pl.SHARP_CODE.match('VS2SA1530AR-1Y')
    assert pl.SHARP_FAMILY.match('RH-EX1026CEZZY')


def test_sharp_plugs_are_connectors():
    assert pl.part_type('Plug, 13Pin(RA)', ['P101']) == 'connector'
    assert pl.part_type('Shorting Plug 2', ['R0101']) == 'resistor'


@pytest.mark.parametrize('desc,ref,kind', [
    ('N J DIO SW 150mA 75V DO-35-2P', 'D7323', 'diode'),           # a switching diode
    ('SWITCHING 1N4148W 0.15A 75V SOD-123', 'D1', 'diode'),
    ('IC-RF SWITCH', 'U1206', 'ic'), ('IC,Hall Effect Switch', 'U3', 'ic'),
    ('PUSH SW NPS-111-S681', 'S1', 'switch'), ('SWITCH, SLIDE', 'SW1', 'switch'), ('TACT SW', 'SW2', 'switch'),
    ('SCREW-TAPTITE;BH,+,-,S,M4,L8,ZPC(WHT),SW 1 S.N.A', 'M1', ''),   # SW: a spring washer
    ('SWITCHING REGULATOR', 'U1', 'regulator'),
])
def test_switch_words(desc, ref, kind):
    assert pl.part_type(desc, [ref]) == kind


def test_quantity_column_is_not_description():
    # LG: code, description, quantity, positions - the 1 was read as a 1 ohm resistor
    page = '\n'.join(f' EBC6185{n:04d}         Resistor,Chip                            1     R84{n:02d}' for n in range(10))
    assert pl.parse_page(page)[0] == ('EBC61850000', ['R8400'], 'Resistor,Chip')
    two = ' EBC61856102         Capacitor,Ceramic,Chip                   2     C101,C102'
    assert pl.parse_page(two) == [('EBC61856102', ['C101', 'C102'], 'Capacitor,Ceramic,Chip')]


@pytest.mark.parametrize('desc,ohms', [
    ('Resistor Array 68X4 01', 68.0),                       # Asus-family code RE044680: 68 ohm
    ('Resistor Array 10KX4 01', 10000.0),
    ('1/16W 5% RES, CHIP NETWORK 56X8 (3816)', 56.0),       # Sony; 3816 is the size
    ('1/32W 5% RES, NETWORK 22 (0603X4)', 22.0),            # a size x elements stays
])
def test_resistor_array_value_times_elements(desc, ohms):
    from apps.components.spec_parse import parse_description
    assert parse_description(pl.clean_description(desc), 'resistor')[1]['resistance_ohm'] == ohms


@pytest.mark.parametrize('desc,pf', [
    # TPV; their codes agree (065G0805472.. = 4700 pF): 95 of 95 on the mirror's lists
    ('9JR6500000201 CAP CHIP 0402 2N2 50V X7R +/-10% 1', 2200.0),
    ('3 9JR6500000280 CAP CHIP 4U7 10V Y5V -20%~+80% 0', 4.7e6),
    ('CER 1206 2N2 500V X7R 10% 1', 2200.0),
    ('CAP CHIP 0402 2P2 50V NPO', 2.2),
])
def test_rkm_capacitances(desc, pf):
    from apps.components.spec_parse import parse_description
    assert parse_description(pl.clean_description(desc), 'capacitor')[1]['capacitance_pf'] == pytest.approx(pf)
