"""
Tests for schematic_values: ODM value labels -> component fields.
"""
import json
from pathlib import Path

import pytest

from apps.products.schematic_ocr_utils import group_identical
from apps.products import schematic_values as sv
from apps.products.schematic_values import generic_name, parse_label


@pytest.mark.parametrize('words, designator, kind, specs, package', [
    # Compal: dielectric digit and tolerance letter (checked against five Compal factory BOMs)
    (['0.1U_0402_16V7K'], 'C142', 'capacitor',
     {'capacitance_pf': 100000.0, 'voltage_v': 16.0, 'dielectric': 'X7R', 'tolerance': '10%'}, '0402'),
    (['22U_0603_6.3V6-M'], 'C5', 'capacitor',
     {'capacitance_pf': 22e6, 'voltage_v': 6.3, 'dielectric': 'X5R', 'tolerance': '20%'}, '0603'),
    (['82P_0402_50V8J'], 'C9', 'capacitor',
     {'capacitance_pf': 82.0, 'voltage_v': 50.0, 'dielectric': 'C0G', 'tolerance': '5%'}, '0402'),
    (['0.1U_0402_25V6'], 'PC6', 'capacitor',                   # the tolerance letter left off
     {'capacitance_pf': 100000.0, 'voltage_v': 25.0, 'dielectric': 'X5R'}, '0402'),
    (['4.7K_0402_5%~D'], 'R1', 'resistor', {'resistance_ohm': 4700.0, 'tolerance': '5%'}, '0402'),
    (['100K_0402_1%_NCP15WF104F03RC'], 'RT1', 'thermistor', {'resistance_ohm': 100000.0, 'tolerance': '1%'}, '0402'),
    (['BLM18PG471SN1D_2P'], 'L9', 'ferrite', {'impedance_ohm': 470.0}, '0603'),      # the part number says bead
    # each field on its own line (Apple, Samsung)
    (['1UF', '10%', '6.3V', 'X5R', '0201'], 'C200', 'capacitor',
     {'capacitance_pf': 1e6, 'voltage_v': 6.3, 'tolerance': '10%', 'dielectric': 'X5R'}, '0201'),
    # other ODMs: explicit fields only; their size digits are not guessed
    (['1K/F_4'], 'R8', 'resistor', {'resistance_ohm': 1000.0, 'tolerance': '1%'}, None),
    (['2.2U/6.3V_4'], 'C3', 'capacitor', {'capacitance_pf': 2.2e6, 'voltage_v': 6.3}, None),
    (['*0_04'], 'R5', 'resistor', {'resistance_ohm': 0.0}, None),
])
def test_labels(words, designator, kind, specs, package):
    r = parse_label(words, designator)
    assert (r['kind'], r['specs'], r['package']) == (kind, specs, package)


def test_build_markers_and_foreign_labels():
    r = parse_label(['PX@', '1U_0402_6.3V6K', '0_0402_5%'], 'CV1')       # a neighbour's jumper label
    assert r['specs']['capacitance_pf'] == 1e6 and r['specs']['tolerance'] == '10%'
    assert r['flags'] == ['fitted in build PX only'] and r['confidence'] == 'high'
    assert parse_label(['@', '10K_0402_5%'], 'R9')['flags'] == ['not fitted by default']
    chip = parse_label(['RT8207PGQW'], 'PU501')
    assert (chip['part_number'], chip['maker'], chip['confidence']) == ('RT8207PGQW', None, 'medium')


def test_generic_names_follow_the_site_style():
    assert generic_name('capacitor', {'capacitance_pf': 1e5, 'voltage_v': 16.0, 'dielectric': 'X7R', 'tolerance': '10%'},
                        '0402') == 'CAP 100nF 16V X7R 10% 0402'
    assert generic_name('resistor', {'resistance_ohm': 0.0}, '0805') == 'RES 0R JUMPER 0805'
    assert generic_name('resistor', {'resistance_ohm': 4700.0, 'tolerance': '5%'}, '0402') == 'RES 4.7K 5% 0402'
    assert generic_name('capacitor', {}, '0402') is None


def test_identical_parts_are_one_row():
    row = {'part_number': 'CAP 1uF 6.3V X5R 10% 0402', 'manufacturer': 'Generic', 'component_type': 'capacitor',
           'package_type': '0402', 'description': 'CAP 1uF 6.3V X5R 10% 0402', 'confidence': 'high', 'page_number': 3,
           'quantity': 1, 'extraction_context': 'PDF text'}
    rows = group_identical([{**row, 'reference_designator': r} for r in ('C41', 'C44', 'C61')]
                           + [{**row, 'reference_designator': 'C9', 'description': row['description'] + '; not fitted by default'}])
    assert [(r['reference_designator'], r['quantity']) for r in rows] == [('C41, C44, C61', 3), ('C9', 1)]


@pytest.mark.parametrize('word, designator, odm, specs, package', [
    # size codes read off each ODM's boardviews (footprint against schematic value)
    ('2.2U/6.3V_4', 'C3', 'quanta', {'capacitance_pf': 2.2e6, 'voltage_v': 6.3}, '0402'),
    ('330_5%_2', 'R4', 'quanta', {'resistance_ohm': 330.0, 'tolerance': '5%'}, '0201'),
    ('1K/F_4', 'R8', 'quanta', {'resistance_ohm': 1000.0, 'tolerance': '1%'}, '0402'),
    ('22u_6.3V_X5R_08', 'C5', 'clevo', {'capacitance_pf': 22e6, 'voltage_v': 6.3, 'dielectric': 'X5R'}, '0805'),
    ('2K_5%_2', 'R6', 'inventec', {'resistance_ohm': 2000.0, 'tolerance': '5%'}, '0402'),   # Inventec _2 is 0402
    ('1uF_6.3V_1', 'C7', 'inventec', {'capacitance_pf': 1e6, 'voltage_v': 6.3}, '0201'),
    ('SCD1U25V2KX-GP', 'C8', 'wistron', {'capacitance_pf': 1e5, 'voltage_v': 25.0, 'tolerance': '10%'}, '0402'),
    ('SC4D7U6D3V3KX-GP', 'C9', 'wistron', {'capacitance_pf': 4.7e6, 'voltage_v': 6.3, 'tolerance': '10%'}, '0603'),
    ('24K3R2F-1-GP', 'R9', 'wistron', {'resistance_ohm': 24300.0, 'tolerance': '1%'}, '0402'),
    ('22u6.3X8', 'C10', 'msi', {'capacitance_pf': 22e6, 'voltage_v': 6.3}, '0805'),
    ('1.5K/4', 'R10', 'msi', {'resistance_ohm': 1500.0}, '0402'),
    ('C0.1U25Y0402', 'C11', None, {'capacitance_pf': 1e5, 'voltage_v': 25.0}, '0402'),        # size written out
])
def test_odm_size_codes(word, designator, odm, specs, package):
    r = parse_label([word], designator, odm)
    assert (r['specs'], r['package']) == (specs, package)


def test_a_size_code_is_read_only_for_its_odm():
    # Quanta _2 is 0201 and Inventec _2 is 0402: without the ODM, no size
    assert parse_label(['330_5%_2'], 'R4')['package'] is None
    assert parse_label(['2K_5%_2_DY'], 'R6', 'inventec')['flags'] == ['not fitted by default']


def test_detect_odm():
    from apps.products.schematic_values import detect_odm
    assert detect_odm('Compal Electronics, Inc. LA-C281P ... Compal Electronics, Inc.') == 'compal'
    assert detect_odm('Quanta Computer Inc. DA0Z8GMB8D0 Quanta Computer Inc.') == 'quanta'
    assert detect_odm('Compal Electronics Quanta Computer') is None          # marks disagree


def test_tongfang_labels_once_the_odm_is_known():
    """Tongfang (GK5CN5Z, PF4PN2F...): read off 14 boardviews; its capacitor labels identify it."""
    assert sv.detect_odm('C1 .1U-10-04R-K C2 1U-6.3-04R-K C3 22U-6.3-06R-M') == 'tongfang'
    p = sv.parse_label(['.1U-10-04R-K'], 'C49', odm='tongfang')
    assert (p['specs'], p['package'], p['confidence']) == (
        {'capacitance_pf': 100000.0, 'voltage_v': 10.0, 'dielectric': 'X5R', 'tolerance': '10%'}, '0402', 'high')
    assert sv.parse_label(['47p-50-04N-J'], 'C1', odm='tongfang')['specs']['dielectric'] == 'C0G'
    assert sv.parse_label(['5.1-1-04'], 'R7', odm='tongfang')['specs'] == {'resistance_ohm': 5.1, 'tolerance': '1%'}
    sense = sv.parse_label(['5m-1W-1-1206'], 'RCH6', odm='tongfang')          # lower-case m: milliohm
    assert (sense['specs']['resistance_ohm'], sense['specs']['power_w'], sense['package']) == (0.005, 1.0, '1206')
    assert sv.parse_label(['10M-04'], 'R257', odm='tongfang')['specs']['resistance_ohm'] == 10e6
    option = sv.parse_label(['@100K-06'], 'R11', odm='tongfang')
    assert option['package'] == '0603' and 'build option (@): may not be fitted' in option['flags']
    assert sv.parse_label(['10K-04'], 'R4')['package'] is None          # without the ODM: no size read


@pytest.mark.parametrize('word, designator, specs, package', [
    ('5.1K1%4', 'R1', {'resistance_ohm': 5100.0, 'tolerance': '1%'}, '0402'),
    ('1.96KR1%/4', 'R1', {'resistance_ohm': 1960.0, 'tolerance': '1%'}, '0402'),
    ('680R04', 'R1', {'resistance_ohm': 680.0}, '0402'),
    ('C10U10X5/8', 'C1', {'capacitance_pf': 10e6, 'voltage_v': 10.0}, '0805'),
    ('0.1U/16V/Y/4', 'C1', {'capacitance_pf': 1e5, 'voltage_v': 16.0}, '0402'),
    ('C0.1U16Y2', 'C1', {'capacitance_pf': 1e5, 'voltage_v': 16.0}, '0402'),     # MSI's 2 is 0402 as well
])
def test_msi_tolerance_and_voltage_forms(word, designator, specs, package):
    p = sv.parse_label([word], designator, odm='msi')
    assert (p['specs'], p['package']) == (specs, package)


def test_gigabyte_labels_and_approved_maker_lists():
    p = sv.parse_label(['0.1U/6/Y5V/25V/Z'], 'C1', odm='gigabyte')
    assert (p['specs']['voltage_v'], p['specs']['dielectric'], p['package']) == (25.0, 'Y5V', '0603')
    assert sv.parse_label(['20K/4/1'], 'R1', odm='gigabyte')['specs'] == {'resistance_ohm': 20000.0, 'tolerance': '1%'}
    listed = sv.parse_label(['0201WMJ0103TCE+0201WMJ0103TJE~~MCR006YRTJ103~~RC0201JR-0710KL'], 'R1')
    assert (listed['maker'], listed['part_number'], listed['package']) == ('Yageo', 'RC0201JR-0710KL', '0201')
    assert sv.parse_label(['10KOhm', 'VX_R0402_SMALL'], 'R0410')['package'] == '0402'


BOARDVIEW_LABELS = json.load(open(Path(__file__).parent / 'fixtures' / 'boardview_labels.json'))


@pytest.mark.parametrize('odm', sorted(BOARDVIEW_LABELS))
def test_labels_against_their_boardview_footprints(odm):
    """Labels as printed on real schematics, with the footprint their boardview puts the part on
    (letus.repair mirror, schematic and boardview of the same board). A label read today must keep its
    package; none may be read as a different one."""
    for item in BOARDVIEW_LABELS[odm]:
        got = sv.parse_label([item['label']], item['designator'], odm=odm)['package']
        if item['reads']:
            assert got == item['package'], item
        else:
            assert got in (None, item['package']), item


@pytest.mark.parametrize('label, designator, name', [
    ('25MHZ_18PF_7V25000034', 'Y1', 'XTAL 25MHz 18pF'),                 # Compal
    ('27mhz20p_d', 'X1', 'XTAL 27MHz 20pF'),                           # MSI
    ('XTAL-32D768KHZ-65-GP', 'X1', 'XTAL 32.768kHz'),                  # Wistron: D is the point
    ('38.4MHZ/10ppm', 'Y1', 'XTAL 38.4MHz 10ppm'),                     # Quanta
    ('32.768K-12.5-20-CM315', 'X3', 'XTAL 32.768kHz 12.5pF 20ppm'),    # Tongfang
])
def test_crystal_labels(label, designator, name):
    p = sv.parse_label([label], designator)
    assert sv.generic_name(p['kind'], p['specs'], p['package']) == name


def test_build_options_are_not_grouped_with_fitted_parts():
    from apps.products.schematic_ocr_utils import _candidate
    fitted = _candidate('R1', 1, '10K-04', sv.parse_label(['10K-04'], 'R1', odm='tongfang'), True, 'PDF text')
    option = _candidate('R2', 1, '@10K-04', sv.parse_label(['@10K-04'], 'R2', odm='tongfang'), True, 'PDF text')
    assert len(group_identical([fitted, option])) == 2


@pytest.mark.parametrize('words, designator, specs, package', [
    (['37.4', '1%(0K445)'], 'R176', {'resistance_ohm': 37.4, 'tolerance': '1%'}, None),    # Asus: code in brackets
    (['1K', '(0603)'], 'R3', {'resistance_ohm': 1000.0}, '0603'),
    (['0402', '5%'], 'R20', {'tolerance': '5%'}, '0402'),                                 # a size, not 402 ohms
    (['(36,38)'], 'R2', {}, None),                                                         # a page reference
    (['(4K7)'], 'R5', {'resistance_ohm': 4700.0}, None),                       # the only value is in brackets
    (['1%(0K445)'], 'R6', {'resistance_ohm': 445.0, 'tolerance': '1%'}, None),
    (['(473)'], 'C7', {}, None),                                              # a three-digit code is not read
    (['1.0', '(2010/11/24)'], 'R8', {'resistance_ohm': 1.0}, None),           # a date, not a 2010 size
    (['(12)', '2008/08/11'], 'R11', {}, None),
    (['4.7K', '1(G)', '3(D)'], 'R9', {'resistance_ohm': 4700.0}, None),     # pin names
    (['0.1%', '(30)'], 'R10', {'tolerance': '0.1%'}, None),                  # a page number
])
def test_bracketed_codes_and_bare_sizes(words, designator, specs, package):
    p = sv.parse_label(words, designator)
    assert (p['specs'], p['package']) == (specs, package)


@pytest.mark.parametrize('word, designator, specs, package', [
    ('电阻_20K_0201_1/20W_J', 'R1', {'resistance_ohm': 20000.0, 'power_w': 0.05, 'tolerance': '5%'}, '0201'),
    ('电阻0R(0402-0.0625W-J)', 'R2', {'resistance_ohm': 0.0, 'power_w': 0.0625, 'tolerance': '5%'}, '0402'),
    ('电阻_39欧姆_0201_1/20W_F(±1%)', 'R3', {'resistance_ohm': 39.0, 'power_w': 0.05, 'tolerance': '1%'}, '0201'),
    ('电阻_100毫欧_0402_1/8W_F(±1%)', 'R4', {'resistance_ohm': 0.1, 'power_w': 0.125, 'tolerance': '1%'}, '0402'),
    ('电阻_22KΩ_0201_1/20W_F', 'R5', {'resistance_ohm': 22000.0, 'power_w': 0.05, 'tolerance': '1%'}, '0201'),
    ('电容_1uF_0201_X5R_6.3V_M', 'C1',
     {'capacitance_pf': 1e6, 'dielectric': 'X5R', 'voltage_v': 6.3, 'tolerance': '20%'}, '0201'),
    ('电容1nF(0402-X7R-50V-K)', 'C2', {'capacitance_pf': 1000.0, 'dielectric': 'X7R', 'voltage_v': 50,
                                     'tolerance': '10%'}, '0402'),
    ('电容_5.6pF_CC0201_NP0_50', 'C3', {'capacitance_pf': 5.6, 'dielectric': 'C0G', 'voltage_v': 50}, '0201'),
    ('电容_100nF_0201_16', 'C4', {'capacitance_pf': 1e5, 'voltage_v': 16}, '0201'),
    ('电容_2.2pF_0201_C0G_50V_C', 'C5', {'capacitance_pf': 2.2, 'dielectric': 'C0G', 'voltage_v': 50,
                                        'tolerance': '±0.25pF'}, '0201'),
    ('磁珠_120R/100MHz_0402', 'FB1', {'impedance_ohm': 120.0}, '0402'),
])
def test_chinese_house_labels(word, designator, specs, package):
    p = sv.parse_label([word], designator)
    assert (p['specs'], p['package'], p['confidence']) == (specs, package, 'high')


def test_fractional_power_is_not_watts():
    assert sv.parse_label(['10K_0402_1/16W_5%'], 'R1')['specs']['power_w'] == 0.0625


def test_brackets_holding_fields_are_kept():
    p = sv.parse_label(['10UF/6.3V', '(0603)X5R'], 'C1')
    assert p['package'] == '0603' and p['specs']['dielectric'] == 'X5R'
