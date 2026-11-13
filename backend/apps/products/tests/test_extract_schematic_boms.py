"""
Tests for extract_schematic_boms: a product's schematics become an import_board_bom bundle.
"""
import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command

from apps.products.management.commands.extract_schematic_boms import build_bundle, component_entry
from apps.components.models import ProductComponent
from apps.products.models import Schematic

pytestmark = pytest.mark.django_db


def _row(ref, part_number, maker='Generic', kind='capacitor', confidence='high', specs=None, package='0402',
         value_raw='0.1U_0402_16V7K', page=1, flags=''):
    return {'page_number': page, 'confidence': confidence, 'reference_designator': ref, 'part_number': part_number,
            'manufacturer': maker, 'component_type': kind, 'package_type': package,
            'description': f"{part_number}; schematic label '{value_raw}'" + (f'; {flags}' if flags else ''),
            'specifications': specs if specs is not None else {'capacitance_pf': 100000.0, 'voltage_v': 16.0},
            'value_raw': value_raw, 'quantity': 1, 'location_description': '', 'extraction_context': ''}


ROWS = [
    _row('C1', 'CAP 100nF 16V X7R 0402'), _row('C2', 'CAP 100nF 16V X7R 0402'),
    _row('C3', 'CAP 100nF 16V X7R 0402', confidence='medium', flags='not fitted by default'),
    _row('R1', 'RES 10K 5% 0402', kind='resistor', specs={'resistance_ohm': 10000.0, 'tolerance': '5%'}, value_raw='10K_0402_5%'),
    _row('Q1', '2N7002', maker='', kind='transistor', confidence='medium', specs={}, package='', value_raw='2N7002'),
    _row('U1', 'ISL6605B', maker='', kind='ic', confidence='medium', specs={}, package='', value_raw='ISL6605B'),
    _row('U3', 'ISL6605B', maker='', kind='ic', confidence='medium', specs={}, package='', value_raw='ISL6605B', page=2),
    _row('U2', 'MEMDQS(0)', maker='', kind='ic', confidence='low', specs={}, package='', value_raw='MEMDQS(0)'),
    _row('R9', 'P3V3', maker='', kind='resistor', confidence='low', specs={}, package='', value_raw='P3V3'),
    _row('C7', 'CAP 10nF', confidence='medium', specs={}, package='', value_raw='0.01U'),       # value not parsed: no ratings
    _row('F3', 'TESTHI08', maker='', kind='fuse', confidence='medium', specs={}, package='', value_raw='TESTHI08'),   # a net name on a fuse
    _row('D4', 'DSTBP2', maker='', kind='diode', confidence='medium', specs={}, package='', value_raw='DSTBP2'),      # a net name on a diode
    _row('U7', 'FSBSEL2', maker='', kind='ic', confidence='medium', specs={}, package='', value_raw='FSBSEL2'),       # too few digits
]


@pytest.fixture
def board(product_factory):
    product = product_factory(manufacturer='MSI', model_number='MS-7777', revision='1.0', region='global',
                              import_source='norway-schem:MSI_MS-7777_1.0')
    sch = Schematic(product=product, schematic_type='full_schematic', file_type='pdf', title='MS-7777 schematic')
    sch.file.save('ms7777.pdf', ContentFile(b'%PDF-1.4 stub'), save=False)
    sch.save()
    return product


def test_bundle_keeps_valued_passives_and_marks_chips(board):
    with patch('apps.products.management.commands.extract_schematic_boms.build_candidates_from_schematic_file',
               return_value=ROWS):
        bundle = build_bundle(board)
    assert bundle['source_tag'] == 'schematic-bom:msi-ms-7777-10' and bundle['add_components_to_existing']
    by_pn = {c['part_number']: c for c in bundle['components']}
    assert set(by_pn) == {'CAP 100nF 16V X7R 0402', 'RES 10K 5% 0402', '2N7002', 'ISL6605B'}
    cap = next(c for c in bundle['components'] if 'C1' in c['reference_designators'])
    assert cap['reference_designators'] == ['C1', 'C2'] and cap['quantity'] == 2    # C3's "not fitted" is its own row
    assert cap['specifications'] == {'capacitance_pf': 100000.0, 'voltage_v': 16.0} and not cap.get('unconfirmed')
    assert [c for c in bundle['components'] if c['reference_designators'] == ['C3']][0]['notes'].endswith('not fitted by default')
    assert by_pn['2N7002']['manufacturer'] == 'Generic' and by_pn['2N7002']['unconfirmed']
    assert by_pn['ISL6605B']['unconfirmed'] and by_pn['ISL6605B']['component_type'] == 'ic'
    assert by_pn['ISL6605B']['reference_designators'] == ['U1', 'U3'] and by_pn['ISL6605B']['quantity'] == 2
    assert bundle['stats'] == {'positions': 7, 'parts': 5, 'unconfirmed': 2, 'high': 3, 'medium': 4}


def test_high_only_floor_and_best_row_per_designator(board):
    twice = ROWS + [_row('C1', 'CAP 100nF 16V X7R 0402', confidence='medium', page=4)]   # a second drawing of C1
    with patch('apps.products.management.commands.extract_schematic_boms.build_candidates_from_schematic_file',
               return_value=twice):
        bundle = build_bundle(board, floor=2)
    refs = {r for c in bundle['components'] for r in c['reference_designators']}
    assert refs == {'C1', 'C2', 'R1'}


def test_command_writes_bundles_the_importer_takes(tmp_path, board, user_factory):
    user_factory(is_superuser=True, is_staff=True)
    out = StringIO()
    with patch('apps.products.management.commands.extract_schematic_boms.build_candidates_from_schematic_file',
               return_value=ROWS):
        call_command('extract_schematic_boms', str(tmp_path), '--manufacturer', 'MSI', stdout=out)
    assert '1 bundles written' in out.getvalue()
    bundle = json.loads((tmp_path / 'msi-ms-7777-10' / 'bundle.json').read_text())
    assert bundle['product']['model_number'] == 'MS-7777'

    call_command('import_board_bom', str(tmp_path), stdout=StringIO())
    rows = ProductComponent.objects.filter(product=board)
    assert rows.count() == 5 and rows.filter(needs_review=True).count() == 2
    board.refresh_from_db()
    assert board.import_source == 'norway-schem:MSI_MS-7777_1.0' and board.schematics.count() == 1

    # a product that now has a list is skipped unless --all
    with patch('apps.products.management.commands.extract_schematic_boms.build_candidates_from_schematic_file',
               return_value=ROWS):
        out = StringIO()
        call_command('extract_schematic_boms', str(tmp_path), stdout=out)
    assert '0 bundles written' in out.getvalue()


def test_component_entry_guesses_the_maker_from_the_prefix():
    entry = component_entry({**_row('C5', 'GRM155R71C104KA88D', maker='', specs={}, package='', value_raw='GRM155R71C104KA88D'),
                             'reference_designator': 'C5, C6'})
    assert entry['manufacturer'] == 'Murata' and entry['reference_designators'] == ['C5', 'C6']
    assert entry['unconfirmed'] and entry['quantity'] == 2


def test_catalogue_listed_chips_are_confirmed_with_their_maker(board, component_factory):
    component_factory(manufacturer='Renesas', part_number='ISL6605B', component_type='ic', usage_count=3)
    component_factory(manufacturer='onsemi', part_number='2N7002', component_type='transistor', usage_count=9)
    component_factory(manufacturer='Generic', part_number='2N7002', component_type='transistor', usage_count=20)
    with patch('apps.products.management.commands.extract_schematic_boms.build_candidates_from_schematic_file',
               return_value=ROWS):
        bundle = build_bundle(board)
    by_pn = {c['part_number']: c for c in bundle['components']}
    assert by_pn['ISL6605B']['manufacturer'] == 'Renesas' and not by_pn['ISL6605B']['unconfirmed']
    assert by_pn['2N7002']['manufacturer'] == 'onsemi' and not by_pn['2N7002']['unconfirmed']   # a named maker beats Generic
    assert bundle['stats']['unconfirmed'] == 0


def test_values_with_more_than_three_significant_digits_are_misreads():
    """'1005' (a metric size code), '25201' (a designator number) and '47R0402' read as 47.0402 ohm
    are not parts; E-series values never need more than three significant digits."""
    from apps.products.management.commands.extract_schematic_boms import plausible, usable
    assert plausible({'resistance_ohm': 4700.0}) and plausible({'resistance_ohm': 4.7}) and plausible({'resistance_ohm': 1e6})
    assert plausible({'capacitance_pf': 2.2e7}) and plausible({'capacitance_pf': 0.5}) and plausible({'resistance_ohm': 0.0})
    assert plausible({'resistance_ohm': 49900.0, 'tolerance': '1%'})                     # E96 49.9K
    for bad in ({'resistance_ohm': 1005.0}, {'resistance_ohm': 25201.0}, {'resistance_ohm': 47.0402},
                {'capacitance_pf': 10024.0}, {'inductance_uh': 1.0025}):
        assert not plausible(bad), bad
    assert usable(_row('R1', 'RES 4.7K 0402', specs={'resistance_ohm': 4700.0}, kind='resistor'))
    assert not usable(_row('R2', 'RES 1.005K 0402', specs={'resistance_ohm': 1005.0}, kind='resistor'))


def test_value_words_are_never_usable_chip_part_numbers():
    from apps.products.management.commands.extract_schematic_boms import usable
    row = {'manufacturer': '', 'reference_designator': 'D8', 'part_number': '680Ohm', 'specifications': {}}
    assert not usable(row)
    assert usable({**row, 'part_number': 'BAT54C-7'})
