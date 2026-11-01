"""
Tests for schematic_values: ODM value labels -> component fields.
"""
import pytest

from apps.products.schematic_ocr_utils import group_identical
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
