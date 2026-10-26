"""
Tests for manage.py refresh_component_specs.
"""
import csv
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.components.models import Component, ProductComponent

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
    # the whole title-page text, as an import stored it; the pass cuts it to the title
    comp = component_factory(manufacturer=maker, part_number=pn, component_type=was,
                             description=f'{title} Features Pb-free package', specifications={'source': 'datasheet'})
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


def test_rating_the_parts_own_lines_disagree_on_is_taken_out(tmp_path, component_factory, product_factory):
    # one factory BOM lists the inductor at 400mA, another at 600mA: the import kept one of them
    part = component_factory(manufacturer='Chilisin', part_number='LS0603-1R0J-S', component_type='inductor',
                             package_type='0603', description='INDUCTOR 1UH/50mA (0603) CHILISIN/LS0603-1R0J-S',
                             specifications={'current_a': 0.6, 'inductance_uh': 1.0})
    ProductComponent.objects.create(product=product_factory(), component=part, import_source='norway-bom:x')
    report = tmp_path / 'report.tsv'
    _run('--lines', _lines(tmp_path, {'CHILISIN|LS0603-1R0J-S': [
        ['INDUCTOR 1UH/400mA (0603) CHILISIN/LS0603-1R0J-S     <G>', 30],
        ['P INDUCTOR 1UH/600mA (0603) CHILISIN/LS0603-1R0J-S', 6]]}), '--report', report)
    part.refresh_from_db()
    assert part.specifications == {'inductance_uh': 1.0}
    assert part.description == 'INDUCTOR 1UH/400mA (0603)'
    rows = list(csv.DictReader(report.open(), delimiter='\t'))
    assert rows[0]['removed (disputed, import-written)'] == 'current_a'


def test_rating_nearly_all_the_parts_lines_agree_on_stands(tmp_path, component_factory, product_factory):
    bead = component_factory(manufacturer='JKMT', part_number='B160808D560TT', component_type='ferrite',
                             package_type='0603', description='FERRITE BEAD(0603)560ohm/0.6A JKMT/B160808D560TT',
                             specifications={'impedance_ohm': 560.0, 'current_a': 0.6})
    ProductComponent.objects.create(product=product_factory(), component=bead, import_source='norway-bom:x')
    _run('--lines', _lines(tmp_path, {'JKMT|B160808D560TT': [
        ['FERRITE BEAD(0603)56ohm/0.6A JKMT/B160808D560TT', 14],
        ['FERRITE BEAD(0603)560ohm/0.6A JKMT/B160808D560TT', 1]]}))
    bead.refresh_from_db()
    assert bead.specifications == {'impedance_ohm': 56.0, 'current_a': 0.6}


def test_can_sizes_written_two_ways_are_not_a_dispute(tmp_path, component_factory):
    cap = component_factory(manufacturer='Nichicon', part_number='UHM1C102MPD6CT', component_type='capacitor',
                            package_type='', description='CAP EL 1000U/16V 8*20 DIP-T NICHICON/UHM1C102MPD6CT',
                            specifications={})
    _run('--lines', _lines(tmp_path, {'NICHICON|UHM1C102MPD6CT': [
        ['CAP EL 1000U/16V 8*20 DIP-T NICHICON/UHM1C102MPD6CT    <G>', 29],
        ['CAP EL 1000U/16V 8*20 NICHICON/UHM1C102MPD6CT', 10]]}))
    cap.refresh_from_db()
    assert cap.package_type == 'Radial 8x20 mm'
    assert cap.specifications['capacitance_pf'] == 1e9


def test_fan_controllers_are_not_regulators(component_factory):
    comp = component_factory(manufacturer='Analog Devices', part_number='ADT7467', component_type='regulator',
                             description='dBCool Remote Thermal Monitor and Fan Controller ADT7467 FEATURES '
                                         'Monitors up to 2 remote temperatures, PWM fan drive outputs',
                             specifications={'source': 'datasheet'})
    _run('--types')
    comp.refresh_from_db()
    assert comp.component_type == 'ic'


def test_a_second_pass_changes_nothing(component_factory):
    # datasheet parts are typed from their whole text, which the first pass cuts to the title
    parts = [
        component_factory(manufacturer='Intersil', part_number='HIP6301V', component_type='ic',
                          description='HIP6301V, HIP6302V Microprocessor CORE Voltage Regulator Multi-Phase '
                                      'Buck PWM Controller FEATURES Multi-Phase Power Conversion',
                          specifications={'source': 'datasheet'}),
        component_factory(manufacturer='Samsung', part_number='1209-002345', component_type='ic',
                          description='IC-TOUCH SENSOR', specifications={}),
        component_factory(manufacturer='Samsung', part_number='DC64-01538A', component_type='capacitor',
                          description='DOOR-LOCK S/W', specifications={}),
    ]
    _run('--types')
    first = [Component.objects.get(pk=c.pk).component_type for c in parts]
    assert first == ['regulator', 'sensor', 'switch']
    out = _run('--types', '--dry-run')
    assert 'types: 0' in out and 'descriptions: 0' in out


def test_alternates_typed_ic_get_their_kind_from_their_bom_line(tmp_path, component_factory):
    socket = component_factory(manufacturer='LOTES', part_number='ACA-ZIF-015-004', component_type='ic',
                               description='Factory-approved alternate to FOXCONN PZ93907-3146-03 (ic)',
                               specifications={})
    guard = component_factory(manufacturer='Acme', part_number='AP22802', component_type='ic',
                              description='USB-PD/VBUS current-limiting protection IC, DFN12 package',
                              specifications={})
    _run('--lines', _lines(tmp_path, {'LOTES|ACA-ZIF-015-004': [['ZIF 939P uPGA SMT G/F LOTES/ACA-ZIF-015-004', 1]],
                                      'ACME|AP22802': [['USB-PD/VBUS current-limiting protection IC, DFN12 package', 1]]}),
         '--types')
    socket.refresh_from_db()
    guard.refresh_from_db()
    assert socket.component_type == 'socket'
    assert guard.component_type == 'ic'


def test_values_from_another_manuals_line_for_the_same_part(component_factory, product_factory):
    # one manual lists 2007-000137 as 'R-CHIP', another with its values
    res = component_factory(manufacturer='Samsung', part_number='2007-000137', component_type='resistor',
                            package_type='', description='R-CHIP', specifications={})
    diode = component_factory(manufacturer='Samsung', part_number='0406-001506', component_type='diode',
                              package_type='', description='UCLAMP0541Z', specifications={})
    for comp, notes in ((res, 'Service manual parts list, page 20: R-CHIP'),
                        (res, 'Service manual parts list, pages 16, 17: R-CHIP;2Kohm,5%,1/16W,TP,1005'),
                        (diode, 'Service manual parts list, page 9: UCLAMP0541Z'),
                        (diode, 'Service manual parts list, page 12: DIODE-TVS'),
                        (diode, 'Service manual parts list, page 14: DIODE-TVS')):
        ProductComponent.objects.create(product=product_factory(), component=comp, notes=notes,
                                        import_source='norway-svc:x')
    _run('--types')
    res.refresh_from_db()
    diode.refresh_from_db()
    assert res.specifications == {'resistance_ohm': 2000.0, 'tolerance': '5%', 'power_w': 0.0625}
    assert res.description == 'R-CHIP;2Kohm,5%,1/16W,TP,1005' and res.package_type == '0402'
    assert diode.description == 'UCLAMP0541Z'       # another manual's wording is no better


def test_a_manuals_vendor_part_number_gives_the_values(component_factory, product_factory):
    cap = component_factory(manufacturer='Samsung', part_number='2203-007781', component_type='capacitor',
                            package_type='', description='C-CERAMIC,CHIP', specifications={})
    for notes in ('Service manual parts list, page 3: C-CERAMIC,CHIP',
                  'Service manual parts list, page 8: CL10A226MP8NUNE'):
        ProductComponent.objects.create(product=product_factory(), component=cap, notes=notes,
                                        import_source='norway-svc:x')
    _run()
    cap.refresh_from_db()
    assert cap.specifications['capacitance_pf'] == 22e6 and cap.specifications['voltage_v'] == 10
    assert cap.description == 'C-CERAMIC,CHIP'
