"""
Tests for manage.py refresh_component_specs.
"""
import csv
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.components.models import ProductComponent

pytestmark = pytest.mark.django_db


def _run(*args):
    out = StringIO()
    call_command('refresh_component_specs', *map(str, args), stdout=out)
    return out.getvalue()


def _lines(tmp_path, data):
    path = tmp_path / 'lines.json'
    path.write_text(json.dumps(data))
    return path


def test_borrowed_line_is_replaced_by_the_parts_own(tmp_path, component_factory):
    # created as an alternate under a 1500uF line, later placed as itself: kept the borrowed line
    cap = component_factory(manufacturer='Rubycon', part_number='6.3ZL2200', component_type='capacitor',
                            package_type='', description='CAP EL 1500U/6.3V 8*20 RUBYCON/6.3ZL1500',
                            specifications={})
    lines = _lines(tmp_path, {'RUBYCON|6.3ZL2200': [['CAP EL 2200U/6.3V/ZL 10*23 RUBYCON/6.3ZL2200', 2]]})
    _run('--lines', lines)
    cap.refresh_from_db()
    assert cap.description == 'CAP EL 2200U/6.3V/ZL 10*23'
    assert cap.specifications == {'capacitance_pf': 2200000000.0, 'voltage_v': 6.3, 'dielectric': 'electrolytic'}
    assert cap.package_type == '10x23 mm'


def test_placeholder_alternate_gets_its_own_line_and_values(tmp_path, component_factory):
    alt = component_factory(manufacturer='RALEC', part_number='RTT032322FTP', component_type='ic', package_type='',
                            description='Factory-approved alternate to TA-I RM06FTN2322 (resistor)', specifications={})
    _run('--lines', _lines(tmp_path, {'RALEC|RTT032322FTP': [['RES 23.2K OHM 1/10W(0603)1% RALEC/RTT032322FTP', 5]]}),
         '--types')
    alt.refresh_from_db()
    assert alt.description == 'RES 23.2K OHM 1/10W(0603)1%'
    assert alt.component_type == 'resistor' and alt.package_type == '0603'
    assert alt.specifications == {'resistance_ohm': 23200.0, 'tolerance': '1%', 'power_w': 0.1}


def test_person_written_values_are_never_overwritten(component_factory):
    part = component_factory(manufacturer='Panasonic', part_number='ECJ2VF1H104Z', component_type='capacitor',
                             package_type='0603', description='Ceramic chip capacitor, 50V, 100 nF',
                             specifications={'capacitance_pf': 100000})
    _run()
    part.refresh_from_db()
    assert part.package_type == '0603'                    # the part number says 0805: reported, not changed
    assert part.description == 'Ceramic chip capacitor, 50V, 100 nF'
    assert part.specifications == {'capacitance_pf': 100000, 'voltage_v': 50.0, 'tolerance': '+80/-20%',
                                   'dielectric': 'Y5V'}


def test_import_written_rating_is_corrected_by_the_part_number(component_factory, product_factory):
    # a suggested equivalent stored the BOM line's 1/16W requirement; an RC0603 is rated 1/10W
    part = component_factory(manufacturer='YAGEO', part_number='RC0603FR-07147RL', component_type='resistor',
                             package_type='0603', description='',
                             specifications={'power_w': 0.0625, 'tolerance': '1%', 'resistance_ohm': 147.0})
    ProductComponent.objects.create(product=product_factory(), component=part, import_source='norway-bom:x')
    _run()
    part.refresh_from_db()
    assert part.specifications['power_w'] == 0.1


def test_disputed_value_is_not_filled_and_is_reported(tmp_path, component_factory):
    part = component_factory(manufacturer='YAGEO', part_number='RC0603FR-07735R7L', component_type='resistor',
                             package_type='', description='RES 35.7 OHM 1/10W (0603) 1% YAGEO/ RC0603FR-07735R7L',
                             specifications={})
    report = tmp_path / 'report.tsv'
    _run('--report', report)
    part.refresh_from_db()
    assert 'resistance_ohm' not in part.specifications
    rows = list(csv.DictReader(report.open(), delimiter='\t'))
    assert rows[0]['disputed value (not filled)'] == 'resistance_ohm'


def test_types_follow_the_line_but_not_a_passing_mention(component_factory):
    film = component_factory(manufacturer='Sony', part_number='1-215-397-00', component_type='resistor',
                             description='Metal film resistor, ±1% tolerance, 1/4W', specifications={})
    digital = component_factory(manufacturer='Panasonic', part_number='UN2214', component_type='transistor',
                                description='NPN digital transistor, built-in bias resistors (R1=10k, R2=47k)',
                                specifications={})
    chassis = component_factory(manufacturer='NAD', part_number='66-185002-0', component_type='capacitor',
                                description='Chassis', specifications={})
    _run('--types')
    for c in (film, digital, chassis):
        c.refresh_from_db()
    assert film.component_type == 'resistor'
    assert digital.component_type == 'transistor'
    assert chassis.component_type == 'other'


def test_dry_run_changes_nothing(tmp_path, component_factory):
    alt = component_factory(manufacturer='RALEC', part_number='RTT032322FTP', component_type='ic', package_type='',
                            description='Factory-approved alternate to TA-I RM06FTN2322 (resistor)', specifications={})
    out = _run('--dry-run', '--types')
    alt.refresh_from_db()
    assert out.startswith('DRY RUN') and alt.component_type == 'ic' and alt.specifications == {}


@pytest.mark.parametrize('maker, pn, was, title, now', [
    ('Intersil', 'ISL6612', 'mosfet', 'ISL6612 Advanced Synchronous Rectified Buck MOSFET Driver', 'ic'),
    ('Richtek', 'RT9202', 'mosfet', 'RT9202 Single Synchronous Buck PWM DC-DC Controller', 'regulator'),
    ('onsemi', 'NCP5395T', 'resistor', 'NCP5395T 2/3/4-Phase Controller with On Board Gate Drivers', 'regulator'),
    ('ICS (Renesas)', 'ICS9148B-04', 'crystal', 'ICS9148B-04 Frequency Generator & Integrated Buffers for SDRAM', 'ic'),
    ('Sanyo', '2SK222', 'mosfet', 'N-Channel Junction Silicon FET 2SK222 Low-Noise Amplifier Applications', 'transistor'),
    ('Sanyo', '2SD1111', 'transistor', 'NPN Darlington Transistor 2SD1111 Driver Applications', 'transistor'),
    ('Niko Semiconductor', 'P5506HVG', 'transistor', 'N-Channel Logic Level Enhancement Mode Field Effect Transistor',
     'mosfet'),
    ('Maxim Integrated', 'MAX8552', 'mosfet', '19-2997;; KIT ATION EVALU -PIN TD FN 10 MOSFET 3.0 m x 3.0', 'ic'),
    ('Fairchild (onsemi)', 'FDS6679', 'transistor', 'FDS6679 30 Volt P-Channel PowerTrench MOSFET', 'mosfet'),
])
def test_datasheet_made_components_are_typed_by_function(component_factory, maker, pn, was, title, now):
    comp = component_factory(manufacturer=maker, part_number=pn, component_type=was, description=title,
                             specifications={'source': 'datasheet'})
    _run('--types')
    comp.refresh_from_db()
    assert comp.component_type == now
    assert comp.specifications == {'source': 'datasheet'}         # no ratings read from title-page text


def test_import_written_disputed_value_is_removed(component_factory, product_factory):
    # an earlier import let the part number win: 735.7 ohm from 'RC0603FR-07735R7L' on a 35.7 ohm line
    part = component_factory(manufacturer='YAGEO', part_number='RC0603FR-07735R7L', component_type='resistor',
                             package_type='0603', description='RES 35.7 OHM 1/10W (0603) 1% YAGEO/ RC0603FR-07735R7L',
                             specifications={'resistance_ohm': 735.7, 'tolerance': '1%'})
    ProductComponent.objects.create(product=product_factory(), component=part, import_source='norway-bom:x')
    _run()
    part.refresh_from_db()
    assert 'resistance_ohm' not in part.specifications
