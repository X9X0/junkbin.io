"""
Chip labels from schematics: the reading rules, and the command that confirms rows by
rule or from a distributor verdict file, or drops net-name noise.
"""
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.components.models import Component, ProductComponent
from apps.products import chip_labels as cl
from apps.products.management.commands import confirm_schematic_chips as cmd
from apps.products.management.commands.extract_schematic_boms import UNCONFIRMED

pytestmark = pytest.mark.django_db


def test_candidates_strip_house_decorations():
    assert cl.candidates('1N4148S') == ['1N4148', '1N4148S']
    assert cl.candidates('1N4148-S-LL34-75V') == ['1N4148']
    assert cl.candidates('2N3904S-R')[0] == '2N3904'
    assert cl.candidates('NPN-3904LT1-S-SOT23')[:2] == ['MMBT3904LT1', '2N3904']
    assert cl.candidates('NPN-MBT3904LT1-S-SOT23')[0] == 'MMBT3904LT1'
    assert cl.candidates('LT1087S') == ['LT1087S', 'LT1087']
    assert cl.candidates('TI-LM358-SOIC8') == ['LM358'] and cl.split('TI-LM358-SOIC8')[3] == 'Texas Instruments'
    assert cl.candidates('CLK-ICS-ICS93722BF-SSOP28') == ['ICS93722BF']
    assert cl.candidates('1N4148W-F') == ['1N4148W-F', '1N4148WF']          # a maker's own suffix is kept
    assert cl.split('1N5817-S-DO-241AC')[1] == 'DO241AC' and cl.split('P45N02LD-S-TO252')[1] == 'TO252'


def test_standard_numbers_are_recognised_and_cleaned():
    assert cl.standard_from_label('1N4148S') == '1N4148'
    assert cl.standard_from_label('1N5817SR') == '1N5817'
    assert cl.standard_from_label('2N7002AS') == '2N7002A'
    assert cl.standard_from_label('NPN-3904LT1-S-SOT23') == 'MMBT3904LT1'
    assert cl.standard_from_label('BAT54A-S-SOT23') == 'BAT54A'
    assert cl.standard_from_label('BZV55C3V3') == 'BZV55C3V3'
    assert cl.standard_from_label('SN74CBTD3305CDR') == 'SN74CBTD3305CDR'
    assert cl.standard_from_label('74LVC126') == '74LVC126'
    for own in ('LT1087S', 'W83310DG', 'SI2303DS', 'NDS351AN-S-SOT23', 'LPC47B367', '83627F'):
        assert cl.standard_from_label(own) is None, own


def test_junk_is_a_net_name_or_a_bare_package_only():
    for j in ('DMICLK100P', '1394CLK', 'PCICLK1394', '619RST', 'VCC33USB4', 'Vss122', 'VDD3V66', 'SOT-223', 'TO-252', 'BGA-508'):
        assert cl.junk(j), j
    for part in ('LPC47B367', 'LAN8700', 'MIC5236YM', 'SN74CB3Q3306APWR', 'PI2PCIE2422', '83627F', 'SC431S', 'W83310DG'):
        assert not cl.junk(part), part


def _row(product, component, designator, note=UNCONFIRMED):
    return ProductComponent.objects.create(product=product, component=component, reference_designator=designator,
                                           quantity=1, import_source=f'schematic-bom:{product.slug}',
                                           needs_review=True, notes=f'Schematic label: {component.part_number}; {note}: no BOM')


def _chip(component_factory, label, kind='diode'):
    return component_factory(manufacturer='Generic', part_number=label, component_type=kind, description=label, package_type='')


def test_apply_confirms_standard_numbers_merges_and_drops_junk(product_factory, component_factory, tmp_path, monkeypatch):
    board = product_factory(manufacturer='MSI', model_number='MS-7369', is_approved=True)
    other = product_factory(manufacturer='MSI', model_number='MS-7388', is_approved=True)
    decorated = _chip(component_factory, '1N4148S')                      # standard, no existing 1N4148
    tailed = _chip(component_factory, 'BAT54A-S-SOT23')                   # standard, merges into the existing BAT54A
    existing = component_factory(manufacturer='Generic', part_number='BAT54A', component_type='diode', package_type='')
    lt = _chip(component_factory, 'LT1087S', 'ic')                        # confirmed at DigiKey as LT1087
    noise = _chip(component_factory, 'DMICLK100P', 'ic')                  # checked, not found, net name
    unknown = _chip(component_factory, 'PGA-S478-F02', 'ic')              # checked, not found, a real label: stays
    unchecked = _chip(component_factory, 'W83310DG', 'ic')                # not checked yet: stays
    for c, d in ((decorated, 'D3'), (tailed, 'D7'), (lt, 'U9'), (noise, 'U12'), (unknown, 'U20'), (unchecked, 'U30')):
        _row(board, c, d)
    _row(other, lt, 'U2')
    board.update_component_count()
    verdicts = tmp_path / 'verdicts.json'
    verdicts.write_text(json.dumps({
        'LT1087S': {'status': 'confirmed', 'candidate': 'LT1087', 'mpn': 'LT1087CT', 'manufacturer': 'Linear Technology',
                    'description': 'IC REG LINEAR 5A TO220', 'sources': ['digikey'], 'datasheet_url': 'https://x/lt1087.pdf'},
        'DMICLK100P': {'status': 'notfound', 'tried': ['DMICLK100P']},
        'PGA-S478-F02': {'status': 'notfound', 'tried': ['PGA-S478-F02']},
    }))
    monkeypatch.setattr(cmd, 'VERDICTS', verdicts)

    out = StringIO()
    call_command('confirm_schematic_chips', 'report', stdout=out)
    assert 'standard   parts     2' in out.getvalue() and 'junk       parts     1' in out.getvalue()

    out = StringIO()
    call_command('confirm_schematic_chips', 'apply', '--dry-run', stdout=out)
    assert 'DRY RUN' in out.getvalue() and Component.objects.filter(part_number='1N4148S').exists()

    out = StringIO()
    call_command('confirm_schematic_chips', 'apply', stdout=out)
    assert 'standard 2 parts / 2 rows, confirmed 1 / 2, junk removed 1 / 1' in out.getvalue()

    decorated.refresh_from_db()
    assert decorated.part_number == '1N4148' and decorated.alternative_part_numbers == ['1N4148S']
    row = ProductComponent.objects.get(product=board, reference_designator='D3')
    assert row.component == decorated and not row.needs_review and 'industry-standard' in row.notes and UNCONFIRMED not in row.notes

    assert not Component.objects.filter(part_number='BAT54A-S-SOT23').exists()
    existing.refresh_from_db()
    assert ProductComponent.objects.get(product=board, reference_designator='D7').component == existing
    assert existing.package_type == 'SOT23' and 'BAT54A-S-SOT23' in existing.alternative_part_numbers and existing.usage_count == 1

    lt.refresh_from_db()
    assert (lt.manufacturer, lt.part_number) == ('Linear Technology', 'LT1087CT')
    assert lt.datasheet_url == 'https://x/lt1087.pdf' and lt.usage_count == 2
    assert all('confirmed at digikey' in r.notes and not r.needs_review for r in ProductComponent.objects.filter(component=lt))

    assert not Component.objects.filter(pk=noise.pk).exists()
    assert not ProductComponent.objects.filter(product=board, reference_designator='U12').exists()
    assert ProductComponent.objects.get(product=board, reference_designator='U20').needs_review
    assert ProductComponent.objects.get(product=board, reference_designator='U30').needs_review
    board.refresh_from_db()
    assert board.component_count == 5

    # a second run changes nothing more
    out = StringIO()
    call_command('confirm_schematic_chips', 'apply', stdout=out)
    assert 'standard 0 parts / 0 rows, confirmed 0 / 0, junk removed 0 / 0' in out.getvalue()


def test_line_names_are_split_into_maker_and_number_when_a_distributor_confirms(product_factory, component_factory, tmp_path, monkeypatch):
    from apps.products.import_review import UNCONFIRMED as UNCONFIRMED_LINE
    board = product_factory(manufacturer='ASUS', model_number='P4B', is_approved=True)
    line = component_factory(manufacturer='Generic', part_number='ADI AD1981B(R0.2) TQFP48 AC97 SOUNDMAX CODEC',
                             component_type='ic', description='ADI AD1981B(R0.2) TQFP48 AC97 SOUNDMAX CODEC', package_type='')
    clip = component_factory(manufacturer='Generic', part_number='ANCHOR CLIP FOR TEHAMA CLIP', component_type='other')
    ProductComponent.objects.create(product=board, component=line, reference_designator='U20', quantity=1,
                                    import_source=f'norway-bom:{board.slug}', needs_review=True,
                                    notes=f'Factory BOM line: ADI AD1981B(R0.2) TQFP48; {UNCONFIRMED_LINE}: medium')
    ProductComponent.objects.create(product=board, component=clip, reference_designator='MH1', quantity=1,
                                    import_source=f'norway-bom:{board.slug}')
    assert cl.line_candidates(line.part_number) == ['AD1981B'] and cl.line_candidates(clip.part_number) == []
    verdicts = tmp_path / 'verdicts.json'
    verdicts.write_text(json.dumps({line.part_number: {'status': 'confirmed', 'candidate': 'AD1981B', 'mpn': 'AD1981BJSTZ',
                                                       'manufacturer': 'Analog Devices', 'description': 'IC CODEC AC97', 'sources': ['mouser']}}))
    monkeypatch.setattr(cmd, 'VERDICTS', verdicts)

    out = StringIO()
    call_command('confirm_schematic_chips', 'report', stdout=out)
    assert 'lines   confirmed  parts     1' in out.getvalue() and 'lines   notfound   parts     1' in out.getvalue()
    call_command('confirm_schematic_chips', 'apply', stdout=StringIO())
    line.refresh_from_db()
    assert (line.manufacturer, line.part_number) == ('Analog Devices', 'AD1981BJSTZ')
    assert line.description.startswith('ADI AD1981B') and 'ADI AD1981B(R0.2) TQFP48 AC97 SOUNDMAX CODEC' in line.alternative_part_numbers
    row = ProductComponent.objects.get(reference_designator='U20')
    assert not row.needs_review and 'confirmed at mouser' in row.notes and UNCONFIRMED_LINE not in row.notes
    clip.refresh_from_db()
    assert clip.part_number == 'ANCHOR CLIP FOR TEHAMA CLIP'


def test_family_listings_confirm_the_maker_or_leave_a_multi_sourced_part_generic(product_factory, component_factory, tmp_path, monkeypatch):
    board = product_factory(manufacturer='MSI', model_number='MS-7005', is_approved=True)
    lt = _chip(component_factory, 'LT1087S', 'ic')
    lm = _chip(component_factory, 'TI-LM358-SOIC8', 'ic')
    _row(board, lt, 'U3')
    _row(board, lm, 'U4')
    verdicts = tmp_path / 'verdicts.json'
    verdicts.write_text(json.dumps({
        'LT1087S': {'status': 'prefix', 'candidate': 'LT1087', 'manufacturer': 'Linear Technology', 'makers': ['Linear Technology'],
                    'listed': ['LT1087CT#PBF', 'LT1087IT#PBF'], 'description': 'IC REG LINEAR POS ADJ 5A TO220', 'sources': ['digikey']},
        'TI-LM358-SOIC8': {'status': 'prefix', 'candidate': 'LM358', 'manufacturer': None, 'makers': ['STMicroelectronics', 'Texas Instruments', 'onsemi'],
                           'listed': ['LM358DR', 'LM358DT', 'LM358N'], 'description': 'IC OPAMP GP 2 CIRCUIT 8SOIC', 'sources': ['digikey']},
    }))
    monkeypatch.setattr(cmd, 'VERDICTS', verdicts)
    call_command('confirm_schematic_chips', 'apply', stdout=StringIO())
    lt.refresh_from_db()
    lm.refresh_from_db()
    assert (lt.manufacturer, lt.part_number) == ('Linear Technology', 'LT1087') and lt.alternative_part_numbers == ['LT1087S']
    assert (lm.manufacturer, lm.part_number) == ('Generic', 'LM358') and lm.package_type == 'SOIC8'
    u3, u4 = (ProductComponent.objects.get(reference_designator=d) for d in ('U3', 'U4'))
    assert not u3.needs_review and 'as the family LT1087CT#PBF, LT1087IT#PBF' in u3.notes
    assert 'made by STMicroelectronics, Texas Instruments, onsemi' in u4.notes


def test_a_bare_number_is_never_asked_for_but_a_sot23_number_is_a_transistor():
    assert cl.candidates('3904-S-SOT23')[:2] == ['MMBT3904', '2N3904'] and cl.standard_from_label('3904-S-SOT23') == 'MMBT3904'
    assert cl.candidates('3904') == [] and cl.candidates('775-land') == ['775-LAND', '775LAND']


def test_jis_transistors_are_standard_and_maker_codes_are_not():
    assert cl.standard_from_label('2SB1197K') == '2SB1197K' and cl.standard_from_label('PNP-2SB1197K-S-SOT23') == '2SB1197K'
    assert cl.standard_from_label('BSS138') == 'BSS138' and cl.standard_from_label('BZX84C5V1') == 'BZX84C5V1'
    assert cl.standard_from_label('BSC032N03S') is None and cl.standard_from_label('BSC059N03SG') is None
